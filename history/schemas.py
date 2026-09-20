from pydantic import BaseModel
from typing import Optional, Literal

class HistoryLocation(BaseModel):
    name: str
    latitude: float
    longitude: float
    country: Optional[str] = None
    timezone: str = "Asia/Kolkata"

class HistoryDay(BaseModel):
    date: str
    type: Literal["historical", "forecast"]
    source: str
    temperature_max: Optional[float] = None
    temperature_min: Optional[float] = None
    precipitation: Optional[float] = None
    wind_speed_max: Optional[float] = None
    weather_code: Optional[int] = None

class HistoryResponse(BaseModel):
    location: HistoryLocation
    days: list[HistoryDay]

class DayDetailResponse(BaseModel):
    location: HistoryLocation
    date: str
    type: str
    source: str
    daily: dict
    hourly: list[dict]
