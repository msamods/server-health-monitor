import os
import platform
import socket
import time
import urllib.request
from datetime import datetime, timedelta
import psutil

# Cache public IP to avoid hitting external API too frequently
_CACHED_IP = None
_CACHED_IP_TIME = 0


def format_bytes(bytes_count: float) -> str:
    """Format raw bytes into human readable string (KB, MB, GB, TB)."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if bytes_count < 1024.0:
            return f"{bytes_count:.2f} {unit}"
        bytes_count /= 1024.0
    return f"{bytes_count:.2f} PB"


def render_progress_bar(percent: float, length: int = 10) -> str:
    """Render a visual ASCII/Unicode progress bar."""
    percent = max(0.0, min(100.0, percent))
    filled_length = int(length * percent // 100)
    bar = "█" * filled_length + "░" * (length - filled_length)
    return f"[{bar}] {percent:.1f}%"


def get_uptime() -> str:
    """Get system uptime formatted as human-readable string."""
    boot_time = datetime.fromtimestamp(psutil.boot_time())
    now = datetime.now()
    uptime = now - boot_time
    days = uptime.days
    hours, remainder = divmod(uptime.seconds, 3600)
    minutes, _ = divmod(remainder, 60)

    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0 or days > 0:
        parts.append(f"{hours}h")
    parts.append(f"{minutes}m")
    return " ".join(parts)


def get_public_ip() -> str:
    """Fetch public IP address with 3-minute local cache and timeout."""
    global _CACHED_IP, _CACHED_IP_TIME
    current_time = time.time()

    if _CACHED_IP and (current_time - _CACHED_IP_TIME < 180):
        return _CACHED_IP

    try:
        req = urllib.request.Request(
            "https://api.ipify.org",
            headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=3) as response:
            _CACHED_IP = response.read().decode("utf-8").strip()
            _CACHED_IP_TIME = current_time
            return _CACHED_IP
    except Exception:
        # Fallback to local socket IP if external lookup fails
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return f"{ip} (local)"
        except Exception:
            return "Unavailable"


def get_system_overview() -> dict:
    """Collect general system information."""
    uname = platform.uname()
    load_avg = None
    if hasattr(os, "getloadavg"):
        try:
            load_avg = [f"{x:.2f}" for x in os.getloadavg()]
        except Exception:
            pass

    return {
        "hostname": socket.gethostname(),
        "os": f"{uname.system} {uname.release}",
        "arch": uname.machine,
        "uptime": get_uptime(),
        "public_ip": get_public_ip(),
        "load_avg": load_avg,
    }


def get_cpu_stats() -> dict:
    """Get detailed CPU statistics."""
    # psutil.cpu_percent with interval=0.5 gives a reliable current reading
    overall_usage = psutil.cpu_percent(interval=0.5)
    per_cpu = psutil.cpu_percent(percpu=True)
    logical_cores = psutil.cpu_count(logical=True)
    physical_cores = psutil.cpu_count(logical=False) or logical_cores

    freq = None
    try:
        cpu_freq = psutil.cpu_freq()
        if cpu_freq and cpu_freq.current:
            freq = f"{cpu_freq.current:.0f} MHz"
    except Exception:
        pass

    return {
        "usage_percent": overall_usage,
        "per_cpu": per_cpu,
        "logical_cores": logical_cores,
        "physical_cores": physical_cores,
        "frequency": freq,
        "bar": render_progress_bar(overall_usage),
    }


def get_ram_stats() -> dict:
    """Get RAM and Swap memory usage."""
    vm = psutil.virtual_memory()
    sm = psutil.swap_memory()

    return {
        "total": format_bytes(vm.total),
        "used": format_bytes(vm.used),
        "available": format_bytes(vm.available),
        "percent": vm.percent,
        "bar": render_progress_bar(vm.percent),
        "swap_total": format_bytes(sm.total),
        "swap_used": format_bytes(sm.used),
        "swap_percent": sm.percent,
        "swap_bar": render_progress_bar(sm.percent) if sm.total > 0 else "N/A",
    }


def get_disk_stats() -> list:
    """Get disk statistics for all unique physical partitions."""
    partitions = psutil.disk_partitions(all=False)
    results = []
    seen_devices = set()

    for p in partitions:
        # Ignore pseudo, cdrom, and duplicate mounts
        if p.device in seen_devices or "loop" in p.device or "snap" in p.mountpoint:
            continue
        try:
            usage = psutil.disk_usage(p.mountpoint)
            seen_devices.add(p.device)
            results.append({
                "mount": p.mountpoint,
                "device": p.device,
                "fstype": p.fstype,
                "total": format_bytes(usage.total),
                "used": format_bytes(usage.used),
                "free": format_bytes(usage.free),
                "percent": usage.percent,
                "bar": render_progress_bar(usage.percent),
            })
        except (PermissionError, OSError):
            continue

    # Fallback to root if empty
    if not results:
        try:
            root_usage = psutil.disk_usage("/")
            results.append({
                "mount": "/",
                "device": "root",
                "fstype": "unknown",
                "total": format_bytes(root_usage.total),
                "used": format_bytes(root_usage.used),
                "free": format_bytes(root_usage.free),
                "percent": root_usage.percent,
                "bar": render_progress_bar(root_usage.percent),
            })
        except Exception:
            pass

    return results


def get_network_stats() -> dict:
    """Get network IO statistics."""
    net_io = psutil.net_io_counters()
    return {
        "bytes_sent": format_bytes(net_io.bytes_sent),
        "bytes_recv": format_bytes(net_io.bytes_recv),
        "packets_sent": net_io.packets_sent,
        "packets_recv": net_io.packets_recv,
    }


def get_top_processes(limit: int = 5) -> dict:
    """Get top CPU and Memory consuming processes."""
    processes = []
    for proc in psutil.process_iter(["pid", "name", "username", "cpu_percent", "memory_percent", "memory_info"]):
        try:
            info = proc.info
            if info["name"]:
                rss = info["memory_info"].rss if info["memory_info"] else 0
                processes.append({
                    "pid": info["pid"],
                    "name": info["name"][:18],
                    "user": (info["username"] or "root")[:10],
                    "cpu_percent": info["cpu_percent"] or 0.0,
                    "mem_percent": info["memory_percent"] or 0.0,
                    "mem_rss": format_bytes(rss),
                })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    top_cpu = sorted(processes, key=lambda x: x["cpu_percent"], reverse=True)[:limit]
    top_mem = sorted(processes, key=lambda x: x["mem_percent"], reverse=True)[:limit]

    return {
        "top_cpu": top_cpu,
        "top_mem": top_mem,
    }
