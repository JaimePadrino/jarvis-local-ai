"""
System Stats Service — single source of truth for CPU, RAM, disk metrics.

Used by both the web server and desktop GUI to avoid duplicated psutil calls.
"""
import os
import logging

log = logging.getLogger("jarvis.backend.services.stats")

_stats_data = {
    "cpu": 0,
    "ram_used": 0.0,
    "ram_total": 0.0,
    "disk_free": 0,
    "disk_total": 0,
}


def get_stats() -> dict:
    """Return current system stats. Safe to call from any thread."""
    try:
        import psutil
        cpu = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage(os.path.abspath(os.sep))
        _stats_data["cpu"] = round(cpu)
        _stats_data["ram_used"] = round(mem.used / (1024 ** 3), 1)
        _stats_data["ram_total"] = round(mem.total / (1024 ** 3), 1)
        _stats_data["disk_free"] = round(disk.free / (1024 ** 3))
        _stats_data["disk_total"] = round(disk.total / (1024 ** 3))
    except Exception as e:
        log.debug(f"Stats collection failed: {e}")
    return dict(_stats_data)


def get_disk_free_text() -> str:
    """Return human-readable disk free/total string."""
    try:
        import psutil
        d = psutil.disk_usage(os.path.abspath(os.sep))
        return f"{d.free / (1024 ** 3):.0f}/{d.total / (1024 ** 3):.0f} GB"
    except Exception:
        return "—"
