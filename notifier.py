import time
import threading
import logging
from typing import Dict, Set
import psutil

import config
import monitor
import docker_monitor

logger = logging.getLogger(__name__)

# State trackers for alert cooling and recovery notifications
_last_cpu_alert_time: float = 0
_cpu_alert_active: bool = False
_consecutive_high_cpu: int = 0

_last_ram_alert_time: float = 0
_ram_alert_active: bool = False

_last_disk_alerts: Dict[str, float] = {}
_known_crashed_containers: Set[str] = set()


def broadcast_alert(bot, message: str) -> None:
    """Send an alert message to all configured admin chat IDs."""
    if not config.ADMIN_CHAT_IDS:
        logger.warning("No ADMIN_CHAT_IDS configured. Cannot send alerts.")
        return

    for chat_id in config.ADMIN_CHAT_IDS:
        try:
            bot.send_message(chat_id=chat_id, text=message, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Failed to send alert to {chat_id}: {e}")


def check_system_and_notify(bot) -> None:
    """Perform periodic checks against thresholds and notify admins if needed."""
    global _last_cpu_alert_time, _cpu_alert_active, _consecutive_high_cpu
    global _last_ram_alert_time, _ram_alert_active
    global _last_disk_alerts, _known_crashed_containers

    now = time.time()
    server_tag = f"<b>[{config.SERVER_NAME}]</b>"

    # --- 1. CPU Check ---
    cpu_usage = psutil.cpu_percent(interval=1.0)
    if cpu_usage >= config.CPU_THRESHOLD:
        _consecutive_high_cpu += 1
        # Require 2 consecutive checks to avoid temporary spike spam
        if _consecutive_high_cpu >= 2:
            if not _cpu_alert_active or (now - _last_cpu_alert_time >= config.ALERT_COOLDOWN):
                top_procs = monitor.get_top_processes(limit=3)["top_cpu"]
                proc_lines = "\n".join([f"  • {p['name']} (PID: {p['pid']}): {p['cpu_percent']}%" for p in top_procs])
                
                msg = (
                    f"⚠️ {server_tag} <b>High CPU Alert!</b>\n\n"
                    f"Current CPU Usage: <code>{cpu_usage:.1f}%</code> (Threshold: {config.CPU_THRESHOLD}%)\n"
                    f"Load Bar: {monitor.render_progress_bar(cpu_usage)}\n\n"
                    f"<b>Top CPU Processes:</b>\n{proc_lines}\n\n"
                    f"⏰ <i>Time: {time.strftime('%Y-%m-%d %H:%M:%S')}</i>"
                )
                broadcast_alert(bot, msg)
                _cpu_alert_active = True
                _last_cpu_alert_time = now
    else:
        # Check for recovery
        if _cpu_alert_active and cpu_usage < (config.CPU_THRESHOLD - 10):
            msg = (
                f"🟢 {server_tag} <b>CPU Usage Recovered</b>\n\n"
                f"CPU has returned to normal levels: <code>{cpu_usage:.1f}%</code>\n"
                f"⏰ <i>Time: {time.strftime('%Y-%m-%d %H:%M:%S')}</i>"
            )
            broadcast_alert(bot, msg)
            _cpu_alert_active = False
        _consecutive_high_cpu = 0

    # --- 2. RAM Check ---
    ram = psutil.virtual_memory()
    if ram.percent >= config.RAM_THRESHOLD:
        if not _ram_alert_active or (now - _last_ram_alert_time >= config.ALERT_COOLDOWN):
            top_procs = monitor.get_top_processes(limit=3)["top_mem"]
            proc_lines = "\n".join([f"  • {p['name']} (PID: {p['pid']}): {p['mem_rss']}" for p in top_procs])
            
            msg = (
                f"🚨 {server_tag} <b>High RAM Alert!</b>\n\n"
                f"Current Memory Usage: <code>{ram.percent:.1f}%</code> (Threshold: {config.RAM_THRESHOLD}%)\n"
                f"Used: <code>{monitor.format_bytes(ram.used)}</code> / <code>{monitor.format_bytes(ram.total)}</code>\n"
                f"Bar: {monitor.render_progress_bar(ram.percent)}\n\n"
                f"<b>Top Memory Processes:</b>\n{proc_lines}\n\n"
                f"⏰ <i>Time: {time.strftime('%Y-%m-%d %H:%M:%S')}</i>"
            )
            broadcast_alert(bot, msg)
            _ram_alert_active = True
            _last_ram_alert_time = now
    else:
        # Check for recovery
        if _ram_alert_active and ram.percent < (config.RAM_THRESHOLD - 5):
            msg = (
                f"🟢 {server_tag} <b>Memory Usage Recovered</b>\n\n"
                f"RAM has returned to safe levels: <code>{ram.percent:.1f}%</code>\n"
                f"⏰ <i>Time: {time.strftime('%Y-%m-%d %H:%M:%S')}</i>"
            )
            broadcast_alert(bot, msg)
            _ram_alert_active = False

    # --- 3. Disk Space Check ---
    disks = monitor.get_disk_stats()
    for d in disks:
        mount = d["mount"]
        pct = d["percent"]
        if pct >= config.DISK_THRESHOLD:
            last_alert = _last_disk_alerts.get(mount, 0)
            if now - last_alert >= config.ALERT_COOLDOWN:
                msg = (
                    f"💾 {server_tag} <b>Low Disk Space Warning!</b>\n\n"
                    f"Mount: <code>{mount}</code>\n"
                    f"Usage: <code>{pct:.1f}%</code> (Threshold: {config.DISK_THRESHOLD}%)\n"
                    f"Used: <code>{d['used']}</code> / Total: <code>{d['total']}</code>\n"
                    f"Free remaining: <code>{d['free']}</code>\n"
                    f"Bar: {d['bar']}\n\n"
                    f"⚠️ <i>Please clean up logs or old backups soon.</i>"
                )
                broadcast_alert(bot, msg)
                _last_disk_alerts[mount] = now

    # --- 4. Docker Crash Check ---
    if config.ENABLE_DOCKER:
        crashed = docker_monitor.get_crashed_containers()
        current_crashed_ids = {c["id"] for c in crashed}

        # Alert for new crashes
        new_crashes = [c for c in crashed if c["id"] not in _known_crashed_containers]
        for c in new_crashes:
            msg = (
                f"🐳 {server_tag} <b>Docker Container Crashed!</b>\n\n"
                f"Name: <b>{c['name']}</b> (ID: <code>{c['id']}</code>)\n"
                f"Exit Code: <code>{c['exit_code']}</code>\n"
                f"Error: <code>{c['error']}</code>\n\n"
                f"⏰ <i>Time: {time.strftime('%Y-%m-%d %H:%M:%S')}</i>"
            )
            broadcast_alert(bot, msg)

        _known_crashed_containers = current_crashed_ids


def start_monitoring_worker(bot):
    """Start background monitoring thread."""
    def worker():
        logger.info(f"Background monitoring thread started. Checking every {config.CHECK_INTERVAL}s.")
        # Initial sleep to allow bot to start polling cleanly
        time.sleep(5)
        while True:
            try:
                check_system_and_notify(bot)
            except Exception as e:
                logger.error(f"Error in monitor worker: {e}", exc_info=True)
            time.sleep(config.CHECK_INTERVAL)

    t = threading.Thread(target=worker, daemon=True, name="VPSMonitorWorker")
    t.start()
    return t
