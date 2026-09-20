"""History service — split past vs forecast, normalize, merge."""

from datetime import date, timedelta
from zoneinfo import ZoneInfo
from .providers.open_meteo import get_historical_weather, get_forecast_weather

IST = ZoneInfo("Asia/Kolkata")

def get_history(latitude: float, longitude: float, start_date: str, end_date: str, location_meta: dict | None = None) -> dict:
    # Parse dates
    sd = date.fromisoformat(start_date)
    ed = date.fromisoformat(end_date)
    if ed < sd:
        raise ValueError("end_date must be >= start_date")
    # limit 60 days for V1
    if (ed - sd).days > 60:
        raise ValueError("Range too large (max 60 days)")

    today = date.today()

    # Split: historical (< today) and forecast (>= today)
    hist_end = min(ed, today - timedelta(days=1)) if sd < today else None
    fore_start = max(sd, today) if ed >= today else None

    days_map: dict[str, dict] = {}

    # Historical part
    if hist_end and hist_end >= sd:
        hs = sd.isoformat()
        he = hist_end.isoformat()
        j = get_historical_weather(latitude, longitude, hs, he, timezone="Asia/Kolkata")
        daily = j.get("daily", {})
        times = daily.get("time", [])
        for i, d in enumerate(times):
            days_map[d] = {
                "date": d,
                "type": "historical",
                "source": "ERA5-Land",
                "temperature_max": (daily.get("temperature_2m_max", [])[i] if i < len(daily.get("temperature_2m_max", [])) else None),
                "temperature_min": (daily.get("temperature_2m_min", [])[i] if i < len(daily.get("temperature_2m_min", [])) else None),
                "precipitation": (daily.get("precipitation_sum", [])[i] if i < len(daily.get("precipitation_sum", [])) else None),
                "wind_speed_max": (daily.get("wind_speed_10m_max", [])[i] if i < len(daily.get("wind_speed_10m_max", [])) else None),
                "weather_code": (daily.get("weather_code", [])[i] if i < len(daily.get("weather_code", [])) else None),
            }

    # Forecast part (includes today)
    if fore_start and fore_start <= ed:
        # Use forecast API with appropriate past_days/forecast_days
        # For simplicity, ask for range covering fore_start..ed via past_days/forecast_days relative to today
        # Compute: past_days for today overlap, forecast_days for future
        # Simplest: request daily via forecast's start_date/end_date params are not supported; use forecast_days to cover range
        # Workaround: call forecast with daily and then filter to requested dates
        # Open-Meteo forecast supports daily for next 16 days; we request enough days to cover ed
        needed_future = (ed - today).days + 1 if ed >= today else 0
        needed_past = 1 if fore_start == today else 0  # to include today
        # Ensure at least 7
        forecast_days = max(7, needed_future)
        past_days = 1 if sd <= today <= ed else 0
        j = get_forecast_weather(latitude, longitude, past_days=past_days, forecast_days=forecast_days, timezone="Asia/Kolkata")
        daily = j.get("daily", {})
        times = daily.get("time", [])
        for i, d in enumerate(times):
            if d < fore_start.isoformat() or d > ed.isoformat():
                continue
            # don't overwrite historical (if overlap, prefer historical for past)
            if d in days_map:
                continue
            days_map[d] = {
                "date": d,
                "type": "forecast",
                "source": "GFS + WeatherGPT ML correction" if d >= today.isoformat() else "GFS",
                "temperature_max": (daily.get("temperature_2m_max", [])[i] if i < len(daily.get("temperature_2m_max", [])) else None),
                "temperature_min": (daily.get("temperature_2m_min", [])[i] if i < len(daily.get("temperature_2m_min", [])) else None),
                "precipitation": (daily.get("precipitation_sum", [])[i] if i < len(daily.get("precipitation_sum", [])) else None),
                "wind_speed_max": (daily.get("wind_speed_10m_max", [])[i] if i < len(daily.get("wind_speed_10m_max", [])) else None),
                "weather_code": (daily.get("weather_code", [])[i] if i < len(daily.get("weather_code", [])) else None),
            }

    # Build sorted list
    sorted_dates = sorted(days_map.keys())
    days = [days_map[d] for d in sorted_dates]
    # Fill missing dates (if gap) with none
    # Ensure all requested dates present
    cur = sd
    full = []
    map_by_date = {d["date"]: d for d in days}
    while cur <= ed:
        ds = cur.isoformat()
        if ds in map_by_date:
            full.append(map_by_date[ds])
        else:
            # missing (beyond 16-day forecast)
            full.append({"date": ds, "type": "unavailable", "source": "N/A", "temperature_max": None, "temperature_min": None, "precipitation": None, "wind_speed_max": None, "weather_code": None})
        cur += timedelta(days=1)

    loc = location_meta or {}
    location = {
        "name": loc.get("name", "Selected location"),
        "latitude": latitude,
        "longitude": longitude,
        "country": loc.get("country"),
        "timezone": "Asia/Kolkata",
    }
    return {"location": location, "days": full}

def get_day_detail(latitude: float, longitude: float, date_str: str, location_meta: dict | None = None) -> dict:
    d = date.fromisoformat(date_str)
    today = date.today()
    is_past = d < today
    source = "ERA5-Land" if is_past else "GFS + WeatherGPT ML correction"
    type_ = "historical" if is_past else "forecast"

    if is_past:
        j = get_historical_weather(latitude, longitude, date_str, date_str, timezone="Asia/Kolkata")
    else:
        # For today/future, get hourly via forecast
        j = get_forecast_weather(latitude, longitude, past_days=1 if d == today else 0, forecast_days=16, timezone="Asia/Kolkata", include_hourly=True)

    daily = j.get("daily", {})
    hourly = j.get("hourly", {})
    # find daily index for date_str
    times = daily.get("time", [])
    daily_data = {}
    if date_str in times:
        idx = times.index(date_str)
        daily_data = {k: (v[idx] if idx < len(v) else None) for k, v in daily.items() if k != "time"}
        daily_data["date"] = date_str
    else:
        daily_data = {"date": date_str}

    # hourly: filter to date_str
    hout = []
    htimes = hourly.get("time", [])
    for i, t in enumerate(htimes):
        if t.startswith(date_str):
            hout.append({k: (v[i] if i < len(v) else None) for k, v in hourly.items()})
            # limit 24
            if len(hout) >= 24:
                break

    loc = location_meta or {}
    location = {"name": loc.get("name", "Selected location"), "latitude": latitude, "longitude": longitude, "country": loc.get("country"), "timezone": "Asia/Kolkata"}
    return {"location": location, "date": date_str, "type": type_, "source": source, "daily": daily_data, "hourly": hout}
