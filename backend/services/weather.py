"""
Weather Service — single source of truth for weather data.

Caches results for 10 minutes. Safe to call from threads or async executors.
"""
import time
import logging

from shared.config import WEATHER_LOCATION

log = logging.getLogger("jarvis.backend.services.weather")

_cache = {
    "text": "",
    "details": {},
    "last_fetch": 0.0,
}


def get_weather() -> dict:
    """Fetch weather data (cached for 10 minutes). Returns dict with 'text' and 'details'."""
    now = time.time()
    if now - _cache["last_fetch"] < 600 and _cache["text"]:
        return _cache

    try:
        import requests
        r = requests.get(
            f"https://wttr.in/{WEATHER_LOCATION}?format=j1",
            timeout=8
        )
        data = r.json()
        current = (data.get("current_condition") or [{}])[0] or {}
        area = (data.get("nearest_area") or [{}])[0] or {}
        location = ((area.get("areaName") or [{}])[0].get("value")) or WEATHER_LOCATION
        temp_c = current.get("temp_C", "--")
        feels_c = current.get("FeelsLikeC", "--")
        humidity = current.get("humidity", "--")
        wind_kmph = current.get("windspeedKmph", "--")
        wind_dir = current.get("winddir16Point", "")
        wdesc = ""
        wdesc_list = current.get("weatherDesc") or []
        if wdesc_list and isinstance(wdesc_list, list):
            wdesc = (wdesc_list[0].get("value") or "").strip()

        _cache["text"] = f"{location}: {temp_c}°C"
        _cache["details"] = {
            "temp": f"{temp_c}°C",
            "location": location,
            "desc": wdesc or "--",
            "humidity": f"{humidity}%",
            "wind": f"{wind_kmph} km/h {wind_dir}".strip(),
            "feelslike": f"{feels_c}°C",
        }
        _cache["last_fetch"] = now
    except Exception as e:
        log.debug(f"Weather fetch failed: {e}")

    return _cache


def get_weather_short() -> str:
    """Return a short weather string like 'Madrid: ☀️ +25°C'."""
    try:
        import requests
        r = requests.get(
            f"https://wttr.in/{WEATHER_LOCATION}?format=3",
            timeout=6
        )
        return (r.text or "").strip()
    except Exception:
        return ""
