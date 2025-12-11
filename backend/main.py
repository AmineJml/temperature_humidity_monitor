from fastapi import FastAPI, WebSocket
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sense_hat import SenseHat
import asyncio, time, os
from pathlib import Path
from dotenv import load_dotenv
import os

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

sense = SenseHat()
sense.low_light = True

latest = {"t": 0, "temp_c": None, "humidity": None}

# ===== Temperature calibration (reduce CPU-heat bias) =====
TEMP_OFFSET = 24.0

def read_env():
    # Use humidity-compensated temperature, then subtract offset
    t = sense.get_temperature_from_humidity() - TEMP_OFFSET
    h = sense.get_humidity()
    return round(t, 2), round(h, 1)

# ====== LED rendering borrowed/adapted from your teammate ======

# Colors (dim/bright variants)
RED_DIM      = (160, 0, 0)
RED_BRIGHT   = (255, 0, 0)
GREEN_DIM    = (0, 120, 0)
GREEN_BRIGHT = (0, 255, 0)
BLUE_DIM     = (0, 0, 80)
BLUE_BRIGHT  = (0, 0, 255)
WHITE        = (255, 255, 255)
BLACK        = (0, 0, 0)

# Temperature range and overheat settings (we’ll use *calibrated* temperature)
T_MIN = -24.0
T_MAX =  40.0                 # Upper bound for 64-pixel fill mapping
OVERHEAT_THRESH = 40.0        # If calibrated temp exceeds this, blink
BLINK_HZ = 2.0                # Blink frequency when overheated

# Current display mode: "temp" or "humidity"
display_mode = "temp"

def clamp(x, lo, hi):
    return max(lo, min(hi, x))

def lerp(a, b, t):
    return a + (b - a) * t

def lerp_color(c1, c2, t):
    t = clamp(t, 0.0, 1.0)
    return (
        int(lerp(c1[0], c2[0], t)),
        int(lerp(c1[1], c2[1], t)),
        int(lerp(c1[2], c2[2], t)),
    )

def temp_color_for(t_c):
    """
    Color mapping for temperature (dim→bright within each zone):
      t <= 0   : Blue    (-24→0)
      0 < t<30 : Green   (0→30)
      t >= 30  : Red     (30→40)
    """
    if t_c is None:
        return BLACK
    if t_c <= 0.0:
        frac = (t_c - T_MIN) / (0.0 - T_MIN)          # 0..1
        return lerp_color(BLUE_DIM, BLUE_BRIGHT, frac)
    elif t_c < 30.0:
        frac = (t_c - 0.0) / 30.0                     # 0..1
        return lerp_color(GREEN_DIM, GREEN_BRIGHT, frac)
    else:
        denom = max(1e-6, (T_MAX - 30.0))
        frac = (t_c - 30.0) / denom                   # 0..1
        return lerp_color(RED_DIM, RED_BRIGHT, frac)

def humidity_color_for(h_pct):
    if h_pct is None:
        return BLACK
    frac = clamp(h_pct / 100.0, 0.0, 1.0)
    return lerp_color(BLUE_DIM, BLUE_BRIGHT, frac)

def make_blank(color=WHITE):
    return [color] * 64

def set_pixel(pixels, x, y, color):
    if 0 <= x < 8 and 0 <= y < 8:
        pixels[y*8 + x] = color

def fill_column(pixels, x, height, color):
    """Fill a column from bottom to top (height: 0..8)"""
    height = clamp(int(round(height)), 0, 8)
    for y in range(7, 7 - height, -1):
        set_pixel(pixels, x, y, color)

def render_overheat_blink():
    """Full-screen red blink at BLINK_HZ."""
    phase = int(time.time() * BLINK_HZ) % 2
    return make_blank(RED_BRIGHT if phase == 0 else BLACK)

async def show_letter_async(letter, back_colour):
    """Show modal letter briefly without blocking the loop too long."""
    sense.show_letter(letter, back_colour=back_colour)
    await asyncio.sleep(1.0)

def render_temperature_pixels(temp_c):
    if temp_c is None:
        return make_blank(BLACK)
    # Overheat alarm if calibrated temp exceeds threshold
    if temp_c > OVERHEAT_THRESH:
        return render_overheat_blink()
    # Map T_MIN..T_MAX to 0..64 filled pixels
    t = clamp(temp_c, T_MIN, T_MAX)
    filled = int(round((t - T_MIN) / (T_MAX - T_MIN) * 64.0))
    color = temp_color_for(t)
    return [color if i < filled else WHITE for i in range(64)]

def render_humidity_pixels(h_pct):
    if h_pct is None:
        return make_blank(BLACK)
    h = clamp(h_pct, 0.0, 100.0)
    height = int(round((h / 100.0) * 8.0))  # 0..8 rows
    color = humidity_color_for(h)
    pixels = make_blank()
    for x in range(8):
        fill_column(pixels, x, height, color)
    return pixels

def draw_led(mode, temp_c, humidity):
    """Update Sense HAT LEDs for the selected mode."""
    if mode == "temp":
        pixels = render_temperature_pixels(temp_c)
    else:
        pixels = render_humidity_pixels(humidity)
    sense.set_pixels(pixels)

def clear_leds():
    try:
        sense.clear()
    except Exception:
        pass

# ===== FastAPI routes =====
@app.get("/api/latest")
async def api_latest():
    return JSONResponse(latest)

@app.websocket("/ws")
async def ws(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            await ws.send_json(latest)
            await asyncio.sleep(1.0)
    except Exception:
        pass

# ===== Background tasks =====
async def sampler():
    """Read sensors, publish 'latest', and render LEDs at 1 Hz."""
    global latest
    while True:
        temp_c, humidity = read_env()
        latest = {"t": int(time.time()), "temp_c": temp_c, "humidity": humidity}
        draw_led(display_mode, temp_c, humidity)
        await asyncio.sleep(1.0)

async def joystick_monitor():
    """
    Poll Sense HAT joystick and toggle display_mode on LEFT/RIGHT.
    Shows 'T' (red) or 'H' (blue) briefly on change.
    """
    global display_mode
    # Tiny delay so startup animation can run first
    await asyncio.sleep(0.1)
    while True:
        switched = False
        for event in sense.stick.get_events():
            if event.action != "released" and event.direction in ("left", "right"):
                display_mode = "humidity" if display_mode == "temp" else "temp"
                switched = True

        if switched:
            # Brief letter flash
            if display_mode == "temp":
                await show_letter_async("T", RED_BRIGHT)
            else:
                await show_letter_async("H", BLUE_BRIGHT)
            # Force immediate redraw with current readings
            draw_led(display_mode, latest.get("temp_c"), latest.get("humidity"))

        await asyncio.sleep(0.05)

# ===== Lifecycle hooks =====
@app.on_event("startup")
async def on_start():
    # Startup animation: flash T then H once
    await show_letter_async("T", RED_BRIGHT)
    await show_letter_async("H", BLUE_BRIGHT)
    asyncio.create_task(sampler())
    asyncio.create_task(joystick_monitor())

@app.on_event("shutdown")
async def on_shutdown():
    clear_leds()

# ===== Static site =====
FRONTEND_DIR = Path(os.getenv("FRONTEND_DIR", str(Path.home() / "IntroES1DT086-Course-Project" / "frontend")))
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="site")
