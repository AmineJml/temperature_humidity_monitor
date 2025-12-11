# Temperature–Humidity Monitor (Raspberry Pi 3 + Sense HAT)

A simple demo that reads indoor **temperature** and **humidity** using the **Sense HAT**, serves the data via a **FastAPI backend**, and visualizes it on both a **web dashboard** and the **Sense HAT LED matrix**.

---

## 🧰 Repository

Clone the project to your Raspberry Pi:

```bash
git clone https://github.com/TDung939/IntroES1DT086-Course-Project.git
cd IntroES1DT086-Course-Project
```

---

## ⚙️ Raspberry Pi Setup

### 1️⃣ Enable I2C Interface

```bash
sudo raspi-config
```

Navigate to:

```
Interface Options → I2C → Enable → Finish → Reboot
```

---

### 2️⃣ Install Required Packages

After reboot:

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip \
                    python3-sense-hat python3-rtimulib i2c-tools
```

---

### 3️⃣ Set Up Python Environment

```bash
cd backend
python3 -m venv .venv --system-site-packages
source .venv/bin/activate
pip install -r requirements.txt
```

---

### 4️⃣ Run the Backend Server

```bash
cd backend
source .venv/bin/activate
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000
```

---

### 5️⃣ Access the Dashboard

Find the Pi’s IP address:

```bash
hostname -I
```

Then open in your browser (from the same network):

```
http://<pi-ip>:8000
```