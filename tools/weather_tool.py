"""Agent-facing weather tool: human time -> GFS + XGBoost"""

from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from typing import Literal
from inference import get_weather, get_latest_available_gfs_run

IST = ZoneInfo("Asia/Kolkata")

def _forecast_hours_for_target(target_ist: datetime) -> int:
    target_utc = target_ist.astimezone(timezone.utc)
    run_time = get_latest_available_gfs_run()
    hours = int((target_utc - run_time).total_seconds() / 3600)
    return max(0, min(hours, 384))  # GFS limit

def get_weather_tool(
    location: str,
    forecast_time: Literal["now", "today", "tomorrow", "day_after_tomorrow"] = "now",
    target_hour: int = 12,
) -> dict:
    """
    Agent tool. Accepts human time, returns structured weather.
    
    forecast_time: now | today | tomorrow | day_after_tomorrow
    Uses IST (Asia/Kolkata) at target_hour (default 12 noon).
    """
    now_ist = datetime.now(IST)

    if forecast_time == "now":
        forecast_hours = 0
        # 0 means closest to now, but ensure >=0 from run
        target_ist = now_ist
        forecast_hours = _forecast_hours_for_target(target_ist)
        # clamp to at least current time delta
        forecast_hours = max(forecast_hours, 0)
    elif forecast_time == "today":
        target_ist = now_ist.replace(hour=target_hour, minute=0, second=0, microsecond=0)
        if target_ist < now_ist:
            target_ist = now_ist  # if past noon, use now
        forecast_hours = _forecast_hours_for_target(target_ist)
    elif forecast_time == "tomorrow":
        target_ist = (now_ist + timedelta(days=1)).replace(hour=target_hour, minute=0, second=0, microsecond=0)
        forecast_hours = _forecast_hours_for_target(target_ist)
    elif forecast_time == "day_after_tomorrow":
        target_ist = (now_ist + timedelta(days=2)).replace(hour=target_hour, minute=0, second=0, microsecond=0)
        forecast_hours = _forecast_hours_for_target(target_ist)
    else:
        # fallback: try parse as string
        return {"success": False, "error": f"Unknown forecast_time: {forecast_time}"}

    result = get_weather(location=location, forecast_hours=forecast_hours)

    # add IST info for agent clarity
    if result.get("success"):
        result["forecast_time_ist"] = target_ist.strftime("%Y-%m-%d %H:%M IST") if forecast_time != "now" else now_ist.strftime("%Y-%m-%d %H:%M IST")
        result["requested"] = {"location": location, "forecast_time": forecast_time, "target_hour": target_hour}

    return result
