# 🛡️ Server Health & Monitor Telegram Bot

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.10+" />
  <img src="https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker Ready" />
  <img src="https://img.shields.io/badge/Telegram-Bot-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white" alt="Telegram Bot" />
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="MIT License" />
  <img src="https://img.shields.io/badge/Architecture-x86__64%20%7C%20ARM64-orange?style=for-the-badge" alt="Arch" />
</p>

An intelligent, lightweight, and production-ready **Telegram Bot** to monitor Linux / VPS servers in real-time. It provides interactive dashboards, Docker container management, and automated background alerts with recovery notifications for CPU, RAM, Disk, and crashed containers.

---

## ✨ Features

- 📊 **Interactive Mobile Dashboard:** Clean ASCII progress bars for CPU, RAM, and Disk storage.
- 🚨 **Smart Anomaly Alerts:**
  - Automated alert when **CPU > 90%** (with top consuming processes breakdown).
  - Automated alert when **RAM > 85%**.
  - Automated warning when **Disk > 90% full**.
  - Automated crash detection when **Docker containers stop unexpectedly**.
- 🟢 **Automatic Recovery Notifications:** Notifies you immediately when CPU or RAM returns to normal levels!
- 🐳 **Docker Container Management:** List running & stopped containers and restart containers directly from Telegram inline buttons.
- 🔥 **Top Process Inspector:** Inspect top 5 CPU & RAM hogging processes on the fly.
- 🌐 **Network & IP Tracking:** Real-time bandwidth IO statistics, public IP tracking, and server latency ping.
- 🔒 **Ironclad Security:** Strict admin whitelist (`ADMIN_CHAT_IDS`). Unauthorized users cannot see server stats or run commands.
- ⚡ **Ultra Lightweight:** Uses ~25MB of RAM with minimal CPU overhead.

---

## 📱 Telegram Dashboard Preview

```text
🖥️ Server Health: My-Ubuntu-VPS
━━━━━━━━━━━━━━━━━━━━
🌐 Host: vps-prod-node01
📍 Public IP: 178.83.59.202
🐧 OS: Linux 6.8.0-generic (x86_64)
⏱️ Uptime: 14d 8h 22m | Load: 0.18, 0.24, 0.15

⚡ CPU: [██░░░░░░░░] 18.5%
🧠 RAM: [██████░░░░] 61.2% (2.45 GB / 4.00 GB)
💾 Disk: [████████░░] 78.4% (31.2 GB / 40.0 GB)
🐳 Docker: 5 running, 0 stopped
━━━━━━━━━━━━━━━━━━━━
⏰ Updated: 17:30:00
```

---

## 🚀 Quick Setup Guide

### Step 1: Create a Telegram Bot
1. Open Telegram and search for [@BotFather](https://t.me/BotFather).
2. Send `/newbot` and follow the instructions to pick a name and username (e.g. `MyVpsHealthBot`).
3. Save the **Bot API Token** (e.g., `7123456789:AAH...`).

### Step 2: Get Your Telegram User ID
1. Search for [@userinfobot](https://t.me/userinfobot) or [@raw_data_bot](https://t.me/raw_data_bot) on Telegram.
2. Send `/start`. The bot will reply with your numerical **Id** (e.g., `123456789`).

---

## 🛠️ Deployment Options

### Option 1: Docker Compose (Recommended)

1. Clone or copy this repository to your server:
   ```bash
   git clone https://github.com/msamods/server-health-monitor.git
   cd server-health-monitor
   ```

2. Create your `.env` configuration file:
   ```bash
   cp .env.example .env
   nano .env
   ```
   Fill in your `BOT_TOKEN`, `ADMIN_CHAT_IDS`, and `SERVER_NAME`.

3. Launch in the background:
   ```bash
   docker compose up -d --build
   ```

4. View logs:
   ```bash
   docker compose logs -f
   ```

---

### Option 2: 1-Click Systemd Service (Native Linux)

If you prefer running without Docker:

```bash
git clone https://github.com/msamods/server-health-monitor.git
cd server-health-monitor

# Run automated installer as root
sudo bash setup.sh
```

Then edit your credentials and start:
```bash
sudo nano /opt/server-health-monitor/.env
sudo systemctl start vps-monitor
sudo systemctl status vps-monitor
```

---

### Option 3: Local / Development Run

```bash
# 1. Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Copy and edit .env
cp .env.example .env

# 4. Start bot
python bot.py
```

---

## 🤖 Available Commands

| Command | Description |
| :--- | :--- |
| `/start` | Welcome screen & full interactive keyboard menu |
| `/status` | Complete server health overview dashboard card |
| `/cpu` | Per-core load bars, physical & logical core count, clock speed |
| `/ram` | Virtual Memory & Swap usage progress bars |
| `/disk` | All mounted disk partitions and free storage space |
| `/docker` | Container status list + one-tap restart buttons |
| `/top` | Top 5 CPU and Memory consuming processes (PID, User, RSS) |
| `/net` | Bandwidth transmitted / received IO and public IP |
| `/ping` | Bot response latency and network connectivity test |

---

## ⚙️ Configuration Parameters (`.env`)

| Variable | Default | Description |
| :--- | :---: | :--- |
| `BOT_TOKEN` | *Required* | Telegram Bot API Token from @BotFather |
| `ADMIN_CHAT_IDS` | *Required* | Comma-separated list of allowed Telegram user IDs |
| `SERVER_NAME` | `VPS-Server` | Nickname for header tags in alert notifications |
| `CHECK_INTERVAL` | `60` | Background monitoring loop interval in seconds |
| `CPU_THRESHOLD` | `90.0` | CPU usage % trigger threshold |
| `RAM_THRESHOLD` | `85.0` | RAM usage % trigger threshold |
| `DISK_THRESHOLD` | `90.0` | Disk usage % trigger threshold |
| `ALERT_COOLDOWN` | `1800` | Minimum seconds between recurring alerts for the same issue (30 mins) |
| `ENABLE_DOCKER` | `true` | Enable Docker container inspections & crash alerts |

---

## 🔒 Security Best Practices

- Never commit your `.env` file to any public Git repository.
- Only whitelist trusted Telegram user IDs in `ADMIN_CHAT_IDS`.
- The bot rejects any message or callback query originating from unauthorized accounts with an `Access Denied` alert.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
