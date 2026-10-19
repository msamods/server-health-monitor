#!/usr/bin/env bash
# ==========================================================
# Automated Setup Script for VPS Server Health & Monitor Bot
# ==========================================================

set -e

INSTALL_DIR="/opt/server-health-monitor"

echo "=========================================================="
echo "🚀 Setting up Server Health Monitor Telegram Bot"
echo "=========================================================="

# Check for root privileges
if [ "$EUID" -ne 0 ]; then
  echo "[-] Please run as root (use: sudo bash setup.sh)"
  exit 1
fi

# 1. Update and install prerequisites
echo "[+] Installing python3, pip, and venv..."
apt-get update -y
apt-get install -y python3 python3-pip python3-venv curl

# 2. Setup directory
echo "[+] Preparing installation directory at $INSTALL_DIR..."
mkdir -p "$INSTALL_DIR"
cp -r ./* "$INSTALL_DIR/"

cd "$INSTALL_DIR"

# 3. Virtual environment
echo "[+] Creating Python virtual environment..."
python3 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt

# 4. Environment file
if [ ! -f .env ]; then
  echo "[+] Creating .env file from template..."
  cp .env.example .env
  echo ""
  echo "⚠️  IMPORTANT: Please edit /opt/server-health-monitor/.env with your BOT_TOKEN and ADMIN_CHAT_IDS."
  echo "    Command: nano /opt/server-health-monitor/.env"
  echo ""
fi

# 5. Systemd service setup
echo "[+] Installing systemd service..."
cp vps-monitor.service /etc/systemd/system/vps-monitor.service
systemctl daemon-reload
systemctl enable vps-monitor.service

echo ""
echo "=========================================================="
echo "✅ Installation completed successfully!"
echo "=========================================================="
echo "Next Steps:"
echo "1. Edit configuration:   nano $INSTALL_DIR/.env"
echo "2. Start the service:     systemctl start vps-monitor"
echo "3. Check live logs:       journalctl -u vps-monitor -f"
echo "=========================================================="
