import os
from typing import Set
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Telegram Bot Token from @BotFather
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "").strip()

# Comma-separated list of Telegram User IDs who have admin rights
raw_admin_ids = os.getenv("ADMIN_CHAT_IDS", "").strip()
ADMIN_CHAT_IDS: Set[int] = set()

if raw_admin_ids:
    for item in raw_admin_ids.split(","):
        item = item.strip()
        if item.isdigit():
            ADMIN_CHAT_IDS.add(int(item))

# Monitoring Interval (in seconds)
CHECK_INTERVAL: int = int(os.getenv("CHECK_INTERVAL", "60"))

# Thresholds for automated alerts
CPU_THRESHOLD: float = float(os.getenv("CPU_THRESHOLD", "90.0"))
RAM_THRESHOLD: float = float(os.getenv("RAM_THRESHOLD", "85.0"))
DISK_THRESHOLD: float = float(os.getenv("DISK_THRESHOLD", "90.0"))

# Alert cooldown in seconds (minimum time before repeating the same alert)
ALERT_COOLDOWN: int = int(os.getenv("ALERT_COOLDOWN", "1800"))  # Default: 30 minutes

# Docker Monitoring flag
ENABLE_DOCKER: bool = os.getenv("ENABLE_DOCKER", "true").lower() in ("true", "1", "yes")

# Server Nickname (useful if running on multiple VPS nodes)
SERVER_NAME: str = os.getenv("SERVER_NAME", "VPS-Server").strip()


def is_admin(user_id: int) -> bool:
    """Check if the given Telegram user ID is in the admin whitelist."""
    if not ADMIN_CHAT_IDS:
        # If no admin IDs are configured yet, allow the first user or log warning
        return False
    return user_id in ADMIN_CHAT_IDS
