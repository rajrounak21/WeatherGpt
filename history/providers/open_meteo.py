"""Open-Meteo providers for history — no LLM.

- Historical: archive-api.open-meteo.com/v1/archive (ERA5, daily/hourly)
- Forecast + recent past: api.open-meteo.com/v1/forecast (past_days + forecast)
"""
import requests

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"

DAILY_VARS = ["weather_code", "temperature_2m_max", "temperature_2m_min", "precipitation_sum", "wind_speed_10m_max"]
HOURLY_VARS = ["temperature_2m", "apparent_temperature", "precipitation", "relative_humidity_2m", "wind_speed_10m", "weather_code"]

def geocode_location(q: str, count: int = 5) -> list[dict]:
    r = requests.get(GEOCODE_URL, params={"name": q, "count": count, "language": "en", "format": "json"}, timeout=10)
    r.raise_for_status()
    j = r.json()
    return j.get("results") or []

def get_historical_weather(latitude: float, longitude: float, start_date: str, end_date: str, timezone: str = "Asia/Kolkata") -> dict:
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "daily": DAILY_VARS,
        "hourly": HOURLY_VARS,
        "timezone": timezone,
    }
    r = requests.get(ARCHIVE_URL, params=params, timeout=15)
    r.raise_for_status()
    return r.json()

def get_forecast_weather(latitude: float, longitude: float, past_days: int = 0, forecast_days: int = 7, timezone: str = "Asia/Kolkata", include_hourly: bool = False) -> dict:
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "daily": DAILY_VARS,
        "timezone": timezone,
        "forecast_days": forecast_days,
        "past_days": past_days,
    }
    if include_hourly:
        params["hourly"] = HOURLY_VARS
    r = requests.get(FORECAST_URL, params=params, timeout=15)
    r.raise_for_status()
    return r.json()

def get_day_hourly(latitude: float, longitude: float, date: str, timezone: str = "Asia/Kolkata") -> dict:
    # Use archive for past, forecast for future — caller decides, but we try both: if date < today use archive
    from datetime import date as _date
    from zoneinfo import ZoneInfo
    today = _date.today().isoformat()  # we use system date; service will pass correct zone
    # If date is past, use archive single day hourly
    if date < today:
        return get_historical_weather(latitude, longitude, date, date, timezone)
    else:
        # for today/future, request hourly for that date via forecast with hourly
        # Forecast hourly returns multi-day; we filter client side
        return get_forecast_weather(latitude, longitude, past_days=0, forecast_days=16, timezone=timezone, include_hourly=True)
