"""WeatherGPT FastAPI — Phase 2: frontend never talks to GFS/Groq directly"""

import sys
sys.stdout.reconfigure(encoding="utf-8")

import io
import re
from pathlib import Path
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from agent.graph import ask
from services.stt import transcribe_bytes
from services.tts import speak_bytes

# alerts — event-driven, NOT agent tool (worker → imd.py → IMD)
try:
    from alerts.db import get_collections, ensure_indexes
except Exception:
    get_collections = ensure_indexes = lambda: (None, None)

from history.router import router as history_router
from study_hub.router import router as study_router
from fastapi.responses import FileResponse

app = FastAPI(title="WeatherGPT API — Phase 2 + History + Study")

app.include_router(history_router)
app.include_router(study_router)

@app.get("/", include_in_schema=False)
def landing():
    return FileResponse("ui/landing.html")

@app.get("/chat", include_in_schema=False)
def chat_page():
    return FileResponse("ui/chat.html")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class ChatReq(BaseModel):
    query: str

class TTSReq(BaseModel):
    text: str
    lang: str = "en"

def detect_lang(text: str) -> str:
    hints = ["kal", "aaj", "mausam", "garmi", "thand", "kaisa", "batao", "hai", "parson", "aane"]
    t = text.lower()
    if any(w in t for w in hints):
        return "hinglish"
    return "en"

def parse_weather(reply: str):
    # temp, humidity, wind from reply; also forecast_time hint
    temp = re.search(r"(\d+\.?\d*)\s*°C", reply)
    hum = re.search(r"(\d+)\s*%\s*humidity", reply, re.I) or re.search(r"humidity[^\d]*(\d+)", reply, re.I)
    wind = re.search(r"wind[^\d]*(\d+\.?\d*)", reply, re.I)
    # location + time not in reply structured, leave for frontend to use query
    return {
        "temperature": float(temp.group(1)) if temp else None,
        "humidity": int(hum.group(1)) if hum else None,
        "wind": float(wind.group(1)) if wind else None,
    }

def make_weather_card(query: str, reply: str):
    w = parse_weather(reply)
    # derive location from query simple heuristic — first capitalized word or known city
    # For Phase 2, keep simple: echo query's location word if reply contains it, else Unknown
    # Frontend will show reply text anyway; card fields are temp/humidity/wind
    return w

@app.post("/chat")
@app.post("/api/chat")
def chat(req: ChatReq):
    raw = ask(req.query)
    clean = raw.replace("**", "").replace("*", "").strip()
    w = make_weather_card(req.query, clean)
    lang = detect_lang(req.query)
    if any(x in clean.lower() for x in ["hai", "hogi", "rahega", "thoda", "rahegi"]):
        lang = "hinglish"
    return {"reply": clean, "lang": lang, "weather": w, "query": req.query}

@app.post("/api/stt")
async def stt(file: UploadFile = File(...)):
    data = await file.read()
    if len(data) > 5 * 1024 * 1024:
        return JSONResponse({"error": "File too large (5MB)"}, status_code=400)
    try:
        text = transcribe_bytes(data, filename=file.filename or "audio.webm")
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
    return {"text": text}

@app.post("/api/tts")
@app.post("/tts")
def tts(req: TTSReq, save: int = 0):
    try:
        wav = speak_bytes(req.text.replace("**","").replace("*",""), lang=req.lang)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
    if save:
        Path("output.wav").write_bytes(wav)
    return StreamingResponse(io.BytesIO(wav), media_type="audio/wav")

# Phase 2: single voice pipeline — stt -> chat -> tts in one call
@app.post("/voice")
@app.post("/api/voice")
async def voice(file: UploadFile = File(...)):
    data = await file.read()
    if len(data) > 5 * 1024 * 1024:
        return JSONResponse({"error": "File too large"}, status_code=400)
    try:
        text = transcribe_bytes(data, filename=file.filename or "audio.webm")
    except Exception as e:
        return JSONResponse({"error": f"STT failed: {e}"}, status_code=500)
    raw = ask(text)
    clean = raw.replace("**","").replace("*","").strip()
    w = make_weather_card(text, clean)
    lang = detect_lang(text)
    if any(x in clean.lower() for x in ["hai", "hogi", "rahega"]):
        lang = "hinglish"
    try:
        wav = speak_bytes(clean, lang=lang)
    except Exception as e:
        return JSONResponse({"error": f"TTS failed: {e}"}, status_code=500)
    # return audio directly with headers for frontend to use
    headers = {"X-Transcript": text, "X-Reply": clean[:800], "X-Lang": lang}
    return StreamingResponse(io.BytesIO(wav), media_type="audio/wav", headers=headers)

class AlertSubscribeReq(BaseModel):
    location_name: str
    district_id: int
    state: str = ""
    push_subscription: dict
    alerts_enabled: bool = True

@app.post("/api/alerts/subscribe")
def alerts_subscribe(req: AlertSubscribeReq):
    subs, _ = get_collections()
    if subs is None:
        return JSONResponse({"error": "DB not configured. Set MONGODB_URI"}, status_code=500)
    ensure_indexes()
    doc = {
        "location_name": req.location_name,
        "district_id": req.district_id,
        "state": req.state,
        "push_subscription": req.push_subscription,
        "alerts_enabled": req.alerts_enabled,
    }
    # upsert by endpoint
    endpoint = req.push_subscription.get("endpoint","")
    try:
        subs.update_one({"push_subscription.endpoint": endpoint}, {"$set": {**doc, "updated_at": __import__("datetime").datetime.utcnow()}, "$setOnInsert": {"created_at": __import__("datetime").datetime.utcnow()}}, upsert=True)
        return {"ok": True, "district_id": req.district_id}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/api/alerts/unsubscribe")
def alerts_unsubscribe(req: dict):
    subs, _ = get_collections()
    if subs is None:
        return JSONResponse({"error": "DB not configured"}, status_code=500)
    endpoint = req.get("endpoint") or req.get("push_subscription",{}).get("endpoint")
    if not endpoint:
        return JSONResponse({"error": "endpoint required"}, status_code=400)
    subs.delete_one({"push_subscription.endpoint": endpoint})
    return {"ok": True}

@app.get("/api/alerts/vapid-public-key")
def vapid_key():
    import os
    return {"publicKey": os.getenv("VAPID_PUBLIC_KEY","")}

@app.get("/api/alerts/stats")
def alerts_stats():
    subs, _ = get_collections()
    if subs is None:
        return {"unique_districts": [], "total": 0}
    try:
        uniq = subs.distinct("district_id", {"alerts_enabled": True})
        total = subs.count_documents({"alerts_enabled": True})
        return {"unique_districts": uniq, "total": total}
    except Exception as e:
        return {"unique_districts": [], "total": 0, "error": str(e)}



@app.on_event("startup")
def start_alert_worker():
    try:
        from alerts.worker import start_scheduler
        sched = start_scheduler()
        if sched:
            print(f"[MAIN] Alert worker scheduled every {__import__('os').getenv('ALERT_POLL_INTERVAL_MIN','15')} min")
    except Exception as e:
        print(f"[MAIN] worker not started: {e}")

@app.get("/api/health")
@app.get("/health")
def health():
    return {"status": "ok"}

ui_dir = Path(__file__).parent / "ui"
if ui_dir.exists():
    app.mount("/", StaticFiles(directory=str(ui_dir), html=True), name="ui")
