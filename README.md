# **Temperature–Humidity Monitor (Raspberry Pi 3 + Sense HAT)**

A lightweight IoT system that reads indoor **temperature** and **humidity** using the **Sense HAT**, exposes the data through a **FastAPI backend**, and visualizes it on both a **responsive web dashboard** and the **Sense HAT LED matrix**.

>This project was developed collaboratively by a team of four students as part of a university course at Uppsala University. I mainly worked on the web interface that displays the sensor data. I also supported the team by keeping track of how the different parts connected. This gave me a good understanding of the overall workflow from hardware integration to backend services and visualization.

>For an overview of the system and its implementation, you can view the presentation below:
>**[Project Presentation](https://uppsalauniversitet-my.sharepoint.com/:p:/g/personal/amine_jamal_6361_student_uu_se/IQDBs29KwxlHSoFawKUMHvKtAVa_84CT_yUPY328Gg-RJfM?e=y1YA2M)**

---

## Repository

Clone the project to your Raspberry Pi:

```bash
git clone https://github.com/TDung939/IntroES1DT086-Course-Project.git
cd IntroES1DT086-Course-Project
```

---

## Raspberry Pi Setup

### Enable I2C Interface

```bash
sudo raspi-config
```

Navigate to:

```
Interface Options → I2C → Enable → Finish → Reboot
```

---

### Install Required Packages

After reboot:

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip \
                    python3-sense-hat python3-rtimulib i2c-tools
```

---

### Set Up Python Environment

```bash
cd backend
python3 -m venv .venv --system-site-packages
source .venv/bin/activate
pip install -r requirements.txt
```

---

### Run the Backend Server

```bash
cd backend
source .venv/bin/activate
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000
```

---

### Access the Dashboard

Find the Pi’s IP address:

```bash
hostname -I
```

Then open in your browser (from the same network):

```
http://<pi-ip>:8000
```
