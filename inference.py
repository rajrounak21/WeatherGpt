import requests
import pickle
import numpy as np
from datetime import datetime, timezone, timedelta


# Load ML model once
with open("model/weathergpt_temperature_xgb.pkl", "rb") as f:
    model = pickle.load(f)


def get_latest_available_gfs_run():
    now = datetime.now(timezone.utc)
    cycle_hour = (now.hour // 6) * 6
    current_run = now.replace(hour=cycle_hour, minute=0, second=0, microsecond=0)
    # GFS runs need ~4h to become available, try up to 4 cycles back
    for back in [6, 12, 18, 24]:
        cand = current_run - timedelta(hours=back)
        try:
            test_params = {
                "latitude": 22.5, "longitude": 88.3, "models": "gfs_global",
                "run": cand.strftime("%Y-%m-%dT%H:%M"),
                "hourly": ["temperature_2m"], "forecast_hours": 1, "timezone": "UTC"
            }
            r = requests.get("https://single-runs-api.open-meteo.com/v1/forecast", params=test_params, timeout=8)
            if r.status_code == 200:
                return cand
        except Exception:
            pass
    return current_run - timedelta(hours=18)


def get_weather(location: str, forecast_hours: int = 24):
    """
    Get GFS weather forecast and apply the WeatherGPT
    XGBoost temperature correction.

    Args:
        location: City or location name.
        forecast_hours: Forecast horizon in hours.

    Returns:
        Dictionary containing weather information.
    """

    # --------------------------------------------------
    # 1. GEOCODING
    # --------------------------------------------------

    geocode_url = "https://geocoding-api.open-meteo.com/v1/search"

    city_params = {
        "name": location,
        "count": 1,
        "language": "en",
        "format": "json"
    }

    city_response = requests.get(
        geocode_url,
        params=city_params,
        timeout=10
    )

    city_response.raise_for_status()

    city_data = city_response.json()

    if not city_data.get("results"):
        return {
            "success": False,
            "error": f"Location '{location}' not found."
        }

    city = city_data["results"][0]

    latitude = city["latitude"]
    longitude = city["longitude"]
    resolved_location = city["name"]

    # --------------------------------------------------
    # 2. GET GFS RUN
    # --------------------------------------------------

    run_time = get_latest_available_gfs_run()

    run_string = run_time.strftime("%Y-%m-%dT%H:%M")

    # --------------------------------------------------
    # 3. GFS FORECAST
    # --------------------------------------------------

    weather_url = "https://single-runs-api.open-meteo.com/v1/forecast"

    weather_params = {
        "latitude": latitude,
        "longitude": longitude,
        "models": "gfs_global",
        "run": run_string,
        "hourly": [
            "temperature_2m",
            "relative_humidity_2m",
            "wind_speed_10m"
        ],
        "forecast_hours": forecast_hours,
        "timezone": "UTC"
    }

    weather_response = requests.get(
        weather_url,
        params=weather_params,
        timeout=15
    )

    weather_response.raise_for_status()

    weather_data = weather_response.json()

    hourly = weather_data["hourly"]

    # --------------------------------------------------
    # 4. SELECT FORECAST TIME
    # --------------------------------------------------

    forecast_index = min(
        forecast_hours,
        len(hourly["time"]) - 1
    )

    time_string = hourly["time"][forecast_index]

    gfs_temperature = hourly["temperature_2m"][forecast_index]
    relative_humidity = hourly["relative_humidity_2m"][forecast_index]
    wind_speed = hourly["wind_speed_10m"][forecast_index]

    # --------------------------------------------------
    # 5. CALCULATE LEAD HOURS
    # --------------------------------------------------

    forecast_time = datetime.fromisoformat(time_string).replace(
        tzinfo=timezone.utc
    )

    lead_hours = int(
        (forecast_time - run_time).total_seconds() / 3600
    )

    # --------------------------------------------------
    # 6. MODEL INPUT
    # --------------------------------------------------

    elevation = weather_data["elevation"]

    hour_utc = forecast_time.hour
    month = forecast_time.month

    model_input = np.array([[
        gfs_temperature,
        relative_humidity,
        wind_speed,
        lead_hours,
        latitude,
        longitude,
        elevation,
        hour_utc,
        month
    ]], dtype=np.float32)

    # --------------------------------------------------
    # 7. XGBOOST CORRECTION
    # --------------------------------------------------

    predicted_error = float(
        model.predict(model_input)[0]
    )

    corrected_temperature = float(
        gfs_temperature + predicted_error
    )

    # --------------------------------------------------
    # 8. RETURN STRUCTURED RESULT
    # --------------------------------------------------

    return {
        "success": True,
        "location": resolved_location,
        "latitude": latitude,
        "longitude": longitude,

        "forecast_time": time_string,
        "lead_hours": lead_hours,

        "gfs_temperature": float(gfs_temperature),
        "predicted_temperature_error": predicted_error,
        "corrected_temperature": corrected_temperature,

        "relative_humidity": relative_humidity,
        "wind_speed": wind_speed,

        "source": "GFS + WeatherGPT XGBoost correction"
    }


# ------------------------------------------------------
# TEST
# ------------------------------------------------------

if __name__ == "__main__":

    result = get_weather(
        location="Kolkata",
        forecast_hours=24
    )

    print(result)