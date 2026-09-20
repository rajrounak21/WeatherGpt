from fastapi import APIRouter, Query, HTTPException
from .providers.open_meteo import geocode_location
from .service import get_history, get_day_detail

router = APIRouter(prefix="/api/history", tags=["history"])

@router.get("/locations")
def locations(q: str = Query(..., min_length=2)):
    try:
        res = geocode_location(q, count=5)
        locs = []
        for r in res:
            locs.append({
                "name": r.get("name"),
                "latitude": r.get("latitude"),
                "longitude": r.get("longitude"),
                "country": r.get("country"),
                "timezone": r.get("timezone") or "Asia/Kolkata",
                "admin1": r.get("admin1"),
            })
        return {"locations": locs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("")
def history(
    latitude: float = Query(...),
    longitude: float = Query(...),
    start_date: str = Query(...),
    end_date: str = Query(...),
    name: str = Query("Selected location"),
    country: str = Query(None),
):
    try:
        data = get_history(latitude, longitude, start_date, end_date, {"name": name, "country": country})
        return data
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/day")
def history_day(
    latitude: float = Query(...),
    longitude: float = Query(...),
    date: str = Query(...),
    name: str = Query("Selected location"),
    country: str = Query(None),
):
    try:
        data = get_day_detail(latitude, longitude, date, {"name": name, "country": country})
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
