// ---- DOM refs
const el = {
  time: document.getElementById("time"),
  date: document.getElementById("date"),
  conn: document.getElementById("conn-status"),
  outsideTemp: document.getElementById("outside-temp"),
  outsideHum: document.getElementById("outside-humidity"),
  indoorTemp: document.getElementById("indoor-temp"),
  indoorHum: document.getElementById("indoor-humidity"),
  tempSlider: document.getElementById("temp-slider"),
  tempFill: document.getElementById("temp-slider-fill"),
  humSlider: document.getElementById("humidity-slider"),
  humFill: document.getElementById("humidity-slider-fill"),
};

function setConn(status, mode) {
  el.conn.textContent = status;
  el.conn.className = "conn-status " + (mode || "conn-off");
}

function fmtNum(n, digits = 1, fallback = "—") {
  const v = Number(n);
  return Number.isFinite(v) ? v.toFixed(digits) : fallback;
}

function clamp(n, min, max) {
  return Math.min(max, Math.max(min, n));
}

function updateClock() {
  const now = new Date();
  el.time.textContent = now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  el.date.textContent = now.toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric" });
}

// Map temp (-20..50) to 0..100% fill (same range as input range)
function setTempUI(tempC) {
  if (!Number.isFinite(tempC)) {
    el.outsideTemp.textContent = "--.-°C";
    el.indoorTemp.textContent = "--.-°C";
    el.tempSlider.value = 0;
    el.tempFill.style.width = "0%";
    return;
  }
  el.outsideTemp.textContent = `${tempC.toFixed(1)}°C`;
  el.indoorTemp.textContent = `${tempC.toFixed(1)}°C`;
  const min = Number(el.tempSlider.min);   // -20
  const max = Number(el.tempSlider.max);   // 50
  const val = clamp(tempC, min, max);
  el.tempSlider.value = val;
  const pct = ((val - min) / (max - min)) * 100;
  el.tempFill.style.width = `${pct}%`;
}

function setHumidityUI(h) {
  if (!Number.isFinite(h)) {
    el.outsideHum.textContent = "--%";
    el.indoorHum.textContent = "--%";
    el.humSlider.value = 0;
    el.humFill.style.width = "0%";
    return;
  }
  const hInt = clamp(Math.round(h), 0, 100);
  el.outsideHum.textContent = `${hInt}%`;
  el.indoorHum.textContent = `${hInt}%`;
  el.humSlider.value = hInt;
  el.humFill.style.width = `${hInt}%`;
}

function updateWeatherUI(data) {
  // backend shape: { t: epochSec, temp_c: float|null, humidity: float|null }
  const temp = Number(data?.temp_c);
  const hum  = Number(data?.humidity);
  setTempUI(temp);
  setHumidityUI(hum);
  updateClock();
}

// ---- Networking: WebSocket with polling fallback
let pollTimer = null;
let retryTimer = null;
let ws = null;

async function pollOnce() {
  try {
    const r = await fetch("/api/latest", { cache: "no-store" });
    const j = await r.json();
    updateWeatherUI(j);
    setConn("Polling /api/latest", "conn-fallback");
  } catch {
    setConn("Offline", "conn-off");
  }
}

function startPolling(intervalMs = 2000) {
  if (pollTimer) return;
  pollTimer = setInterval(pollOnce, intervalMs);
  pollOnce();
}

function stopPolling() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
}

function connectWS() {
  if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) return;

  const proto = location.protocol === "https:" ? "wss" : "ws";
  ws = new WebSocket(`${proto}://${location.host}/ws`);

  ws.onopen = () => {
    setConn("Live via WebSocket", "conn-ok");
    stopPolling();
  };

  ws.onmessage = (ev) => {
    try {
      const data = JSON.parse(ev.data);
      updateWeatherUI(data);
    } catch {
      // ignore malformed packet
    }
  };

  const handleCloseOrError = () => {
    setConn("WS unavailable → polling", "conn-fallback");
    startPolling(2000);
    if (!retryTimer) {
      retryTimer = setInterval(() => {
        connectWS();
        // once open, onopen will clear polling; leave retry running for robustness
      }, 5000);
    }
  };

  ws.onclose = handleCloseOrError;
  ws.onerror = handleCloseOrError;
}

// ---- Boot
updateClock();
setInterval(updateClock, 15_000);
connectWS();
