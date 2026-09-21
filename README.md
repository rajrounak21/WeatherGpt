# WeatherGPT — AI Weather Assistant for India

> **Ask in English or Hinglish, by text or voice — get GFS + ML-corrected forecasts, explore history, get proactive IMD alerts, and learn weather.**

---

## Smart India Hackathon 2026

| | |
|---|---|
| **Problem Statement ID** | SIH26068 (S.No. 68) |
| **Ministry** | Ministry of Earth Sciences (MoES) |
| **Department** | India Meteorological Department (IMD) |
| **Category & Theme** | Software - Disaster Management |
| **Official Title** | WeatherGPT: Conversational AI for Weather Forecasting, Alerts, and Climate Information |
| **GitHub** | [rajrounak21/WeatherGpt](https://github.com/rajrounak21/WeatherGpt) |

### Background and Challenge

Fragmented Weather Information Channels -- Weather information is often distributed through multiple portals, bulletins, satellite products, and forecast systems, making it difficult for common users, researchers, disaster managers, and government agencies to quickly obtain actionable insights.

### Expected Solution

Conversational Intelligence Platform -- Develop WeatherGPT: an intelligent conversational platform integrating meteorological datasets, forecasting models (GFS/WRF), disaster early warnings, location-based advisories, voice interaction for rural accessibility, and multilingual Indian language support.

<p align="center">
  <img src="ui/weathergpt.png" alt="WeatherGPT" width="120" style="border-radius:16px" />
</p>

<p align="center">
  <a href="#features">Features</a> - <a href="#architecture">Architecture</a> - <a href="#langgraph-flow">LangGraph</a> - <a href="#alert-system">Alerts</a> - <a href="#imd-whitelisting">IMD Access</a> - <a href="#model-training">Model</a> - <a href="#quick-start">Quick Start</a> - <a href="#api-reference">API</a>
</p>

---

## Features

| Feature | What it does | Tech |
|---|---|---|
| **1. AI Weather Agent** | `User -> Groq LLM -> weather_tool(location, forecast_time) -> GFS + XGBoost (32.5 C corrected) -> natural reply` in English/Hinglish + `Text + Voice` | `LangGraph`, `ChatGroq(openai/gpt-oss-20b)`, `tools/weather_tool.py`, `Groq Whisper + Orpheus`, XGBoost trained on [Arko007/weathergpt-d1-mos-dataset](https://huggingface.co/datasets/Arko007/weathergpt-d1-mos-dataset) |
| **2. Proactive Alerts** | Worker monitors **IMD District/CAP** warnings in background → `MongoDB` dedup → `Web Push` even when site closed | `alerts/worker.py` + `alerts/providers/imd.py` + `MongoDB` + `pywebpush` |
| **3. Weather History** | Past (`ERA5-Land` `1940→`) + Today + Future (`GFS+ML`) on one timeline — `Past / Today / Future` with `historical` vs `forecast` transparency | `history/providers/open_meteo.py` (`archive-api` + `api.open-meteo`) |
| **4. Study Hub** | Learn → Explore → Quiz (5 Q ~2 min, supportive feedback) → AI explain (`Why does warm air rise?`) → Adaptive practice | `study_hub/content/topics.json` + `study_hub/router.py` + `Groq` teacher mode |
| **Voice** | `STT: Groq whisper-large-v3-turbo` (hi/en auto) ↔ `TTS: Groq orpheus-v1-english` (`wav` `autumn/diana`) | `services/stt.py`, `services/tts.py` |
| **Hinglish** | Understands `Kal Patna me mausam kaisa rahega?` → replies Hinglish Roman; `Will it be hot?` → English | System prompt in `agent/prompts.py` |

Landing: `/` → `Launch App` → `/chat` (see `ui/landing.html` → `ui/chat.html`). No auth, no giant weather DB — **History has no DB; Alerts DB is only `alert_subscriptions + processed_warnings`**.

---

## Architecture

```
                            WEATHERGPT
                                 │
              ┌──────────────────┼───────────────────┐
              ▼                  ▼                   ▼
         AI AGENT           ALERT SYSTEM        HISTORY/STUDY
              │                  │                   │
         LangGraph          Background Worker     FastAPI
              │                  │                   │
         weather_tool         MongoDB            Open-Meteo
              │               ↙      ↘               │
        GFS + XGB        subscriptions processed  ERA5 / GFS
              │               │        │              │
              ▼               └────┬───┘              ▼
          Chat/Voice           Web Push           Timeline UI
```

**Frontend:** `ui/` plain HTML + `style.css` (Inter, CSS vars `light #f1f5f9 / dark #0b1220`, sticky rail `260→64px` + overlay on mobile), `FastAPI StaticFiles` at `/`. Backend is single entry `main.py` + `Chat`/`History`/`Alerts`/`Study` routers.

### Project Structure

```
WeatherGpt/
├── main.py                     # FastAPI single entry (/, /chat, /api/*, StaticFiles ui/)
├── app.py                      # CLI preview: python app.py "Kolkata tomorrow" --voice
├── inference.py                # GFS fetch + XGBoost pickle loader (model/*.pkl)
├── model/
│   ├── weathergpt_temperature_xgb.pkl
│   └── weathergpt_temperature_bias_correction_ipynb.ipynb  # training code (see Model Training)
├── tools/weather_tool.py       # Agent tool: human forecast_time → forecast_hours (IST)
├── agent/
│   ├── graph.py                # StateGraph(agent→tools→agent) with ChatGroq.bind_tools
│   └── prompts.py              # System prompt (Hinglish/English mirroring)
├── services/stt.py / tts.py    # Groq Whisper / Orpheus
├── alerts/
│   ├── db.py                   # MongoDB (alert_subscriptions, processed_warnings)
│   ├── worker.py               # APScheduler every ALERT_POLL_INTERVAL_MIN (distinct district → fetch → normalize → dedup → push)
│   ├── providers/imd.py        # fetch_district_warnings / fetch_cap_alerts
│   ├── engine.py               # normalize → is_new_warning → mark_processed
│   └── push.py                 # pywebpush + VAPID
├── history/
│   ├── router.py               # /api/history, /api/history/locations, /api/history/day
│   ├── service.py              # split historical (<today) vs forecast (>=today) + merge
│   └── providers/open_meteo.py # archive-api + api.open-meteo + geocoding
├── study_hub/
│   ├── content/topics.json     # trusted lessons + quizzes (thunderstorms, humidity, rain, heatwave)
│   └── router.py               # /api/study/topics, /explain, /quiz/*
├── ui/
│   ├── landing.html            # /  (Launch App → /chat)
│   ├── chat.html               # /chat (index.html copy — actual chat app)
│   ├── index.html              # kept for backward compat (also chat)
│   ├── history.html            # /history.html  (?q=Patna via alert tap)
│   ├── alerts.html             # /alerts.html  (Enable per district, View Your enabled)
│   ├── study.html              # /study.html   (Learn → Quiz → Result)
│   ├── style.css               # CSS vars light/dark, rail, premium cards
│   ├── app.js                  # chatView ↔ landingView, voice modal, processing block
│   ├── sw.js                   # push handler: showNotification with actions
│   └── weathergpt.png / favicon.ico / icon-180.png  # favicon + push icon/badge
├── requirements.txt
├── .env.example
└── .env                        # not committed (see Quick Start)
```

---

## LangGraph Flow

Normal Agent (conversation-driven). **Alert System does NOT use LangGraph** — it is event-driven (`worker → imd.py`, no LLM).

```mermaid
graph TD
    A["User: Kal Patna me mausam kaisa rahega"] --> B["LangGraph Agent<br/>ChatGroq openai/gpt-oss-20b<br/>system prompts.py"]
    B --> C{"Tool call?"}
    C -->|"get_weather_tool<br/>location=Patna<br/>forecast_time=tomorrow"| D["tools/weather_tool.py<br/>IST target 12:00 to forecast_hours"]
    D --> E["inference.py<br/>geocode to GFS run to forecast_hours to hourly"]
    E --> F["XGBoost<br/>model weathergpt_temperature_xgb.pkl<br/>predict error to corrected_temperature"]
    F --> G["Tool result<br/>corrected_temperature 32.5C<br/>humidity 49% wind 5.2"]
    G --> B
    B --> H["Groq LLM<br/>natural reply<br/>Hinglish/English"]
    H --> I["Text + Voice<br/>services/tts.py<br/>Orpheus wav"]
```

**StateGraph (`agent/graph.py:17`):**
```python
State = TypedDict(messages=Annotated[list, add_messages])
graph = StateGraph(State)
graph.add_node("agent", agent)          # llm.bind_tools([get_weather_tool])
graph.add_node("tools", ToolNode([get_weather_tool]))
graph.add_edge(START, "agent")
graph.add_conditional_edges("agent", tools_condition, {"tools":"tools", END:END})
graph.add_edge("tools", "agent")
```

Hinglish example: `Kal Kolkata…` → tool call `{"location":"Kolkata","forecast_time":"tomorrow"}` correctly; `Will it be hot tomorrow in Delhi?` → `Delhi`/`tomorrow`.

---

## Alert System — Full Proactive Architecture

> **No per-user polling, no giant weather DB. MongoDB is only `alert_subscriptions` + `processed_warnings`.**

```
User selects district (e.g. Patna → district_id 573 per IMD api.pdf) → Enable Alerts
  → Browser Push Subscription (serviceWorker pushManager.subscribe, VAPID public key)
  → POST /api/alerts/subscribe {location_name, district_id, state, push_subscription} → MongoDB alert_subscriptions
  → User leaves site (push subscription persists)
     ↓
Background Worker (main.py:on_startup → alerts/worker.py:start_scheduler() every ALERT_POLL_INTERVAL_MIN, default 15, configurable)
  → MongoDB distinct(district_id) where alerts_enabled → e.g. [573 Patna, 320 Gaya, 195 Delhi] (10k users → 3 requests, not 10k)
  → alerts/providers/imd.py fetch (CAP first, else District API per unique district)
  → alerts/engine.py normalize → {warning_id, district_id, severity, event, valid_from/until, raw_hash}
  → is_new_warning? (processed_warnings _id check) — YES → push, NO → skip (prevents 10:00/10:15 spam)
  → alerts/push.py find_subscriptions({district_id:573}) → [Browser A,B,C] → pywebpush → OS notification
     🚨 Orange Alert — Patna: Heavy rain warning until 8 PM — tap to see current weather in History
  → mark_processed → _id = warning_id (distributed lock — two workers can't double-send)
```

**Normal Agent vs Alert System:**
```mermaid
graph TD
    U["User"] -->|"asks"| A["Agent<br/>GFS+XGB to reply"]
    I["IMD"] --> W["Worker<br/>every 15 min<br/>IMD to normalize"]
    W --> D{"deduplicate<br/>processed_warnings"}
    D -->|"new"| M["MongoDB find district subs"]
    M --> P["Web Push"]
    P --> U2["Browser<br/>even when site closed"]
```

**MongoDB Collections (`alerts/db.py:1`):**

```js
// alert_subscriptions — one doc per browser enable, no user_id
{
  location_name: "Patna", district_id: 573, state: "Bihar",
  push_subscription: {endpoint:"https://fcm.googleapis.com/...", keys:{p256dh:"...",auth:"..."}},
  alerts_enabled: true, created_at, updated_at
}
// indexes: {district_id:1}, {alerts_enabled:1}

// processed_warnings — dedup, also lock
{
  _id: "573:488c719c6641196e", // warning_id (cap-id or hash)
  district_id: 573, severity:"orange", event:"heavy_rain",
  valid_from, valid_until, raw_hash, processed_at
}
```

**Frontend Alert Flow (`ui/alerts.html:34` → `main.py:133` → `ui/sw.js:1`):**
- Landing/Chat has `Get weather alerts for your district` → `/alerts.html` (separate page, searchable `Patna, Gaya...` datalist, not hardcoded 5-city hack). Any district works — maps to `district_id` via `districtMap` (Patna 573 etc.; free text like `Telgana` → `id:0` → not polled until Phase 0 mapping adds it).
- Enable: `Notification.requestPermission()` → `navigator.serviceWorker.register("/sw.js")` → `pushManager.subscribe({applicationServerKey: VAPID_PUBLIC_KEY})` → `POST /api/alerts/subscribe` (upsert by `push_subscription.endpoint`).
- `Your enabled alerts` list shows `localStorage myAlerts` per-device (Disable → `POST /api/alerts/unsubscribe` + `localStorage` delete + `410 Gone` auto-cleanup in `push.py`).
- Notification: `sw.js:1` `push` → `showNotification(🚨 Orange Alert — Patna, Heavy rain warning until 8 PM — tap to see current weather in History., icon:/weathergpt.png, vibrate, requireInteraction, actions:[View in WeatherGPT,Dismiss])` + `notificationclick` → `clients.openWindow("/history.html?q=Patna")` — history auto-loads `Patna 25.59,85.14` without showing world `Patna Scotland` chips.

---

## IMD Whitelisting — Get Access Via IP (Full)

IMD's **District Warning API** is **IP-whitelisted** — without whitelisting you get `401 IP 106.222.248.13 needs to be whitelisted` (`alerts/providers/imd.py:13`).

**Source docs you verified:**
- IMD `api.pdf` (https://mausam.imd.gov.in/imd_latest/contents/api.pdf) — `warnings_district_api.php?id=<district obj_id>` returns `Day1-4` warning codes per district. The PDF's appendix lists `district name → obj_id` (e.g. `Patna → 573`, `Gaya → 320`).
- WIS2 `CAP Alerts Published by IMD` (https://wis2box.imd.gov.in/oapi/collections/discovery-metadata/items/urn:wmo:md:in-imd:cap_alerts) — alternative where the feed already contains `event/severity/areaDesc/effective/expires` and affected geography, so you may not need per-district polling.

**Steps to get whitelisted:**
1. Find your server's egress IP: `curl ifconfig.me` or check `uvicorn` logs `[IMD DISTRICT] id=573 -> 401 preview=IP 106.222.248.13 needs...` — that `106.222.248.13` is your IP to whitelist.
2. Email IMD API support (contact in `api.pdf` footer or `mausam@imd.gov.in` / IMD Pune `support`): subject `Request to whitelist IP for District Warning API — WeatherGPT alerts`, body: `Application WeatherGPT (proactive district alerts for public), server IP 106.222.248.13, purpose polling IMD District Warning API every 15 min for subscribed districts only (distinct district_id, not per-user), expected RPS ~ N_districts/15min, contact <your email>`. Attach `api.pdf` page reference.
3. While waiting, either:
   - **Mock for local demo:** set `.env` `MOCK_ALERTS=1` — `alerts/providers/imd.py:13` will inject `mock orange heavy_rain` per district so `POST /api/alerts/test` (`main.py:182`) can prove `Web Push` without IMD.
   - **Or switch to CAP:** investigate `wis2box` `cap_alerts` collection; if it returns real alerts with `areaDesc`, make it primary and skip per-district calls.

**Test after whitelisting:**
```bash
curl "https://mausam.imd.gov.in/api/warnings_district_api.php?id=573"
# should return 200 JSON with Day1-4 codes, not 401
# then in WeatherGPT:
uvicorn main:app --reload
# open http://localhost:8000/alerts.html → Enable Patna → wait 15 min or POST /api/alerts/debug
# terminal should show [WORKER] unique districts from DB (filtered >0): [573] → [IMD DISTRICT] id=573 -> 200 → checked 1 new 1
```

**Polling interval:** `main.py` + `alerts/worker.py:10` `ALERT_POLL_INTERVAL_MIN=15` — **configurable env, not hard-coded**. Tune after verifying IMD's `issued_at`/`updated_at` cadence and rate limits. Worker also uses `distinct(district_id)` so `10k users` in `3 districts` → `3` IMD calls per tick, not `10k`.

---

## All Features — How They Work

| Feature | User Flow | Data Path | Why Separate |
|---|---|---|---|
| **Chat** | Type/speak Hinglish → WeatherGPT replies with corrected temp | `Groq → weather_tool → GFS+XB → Groq` | LLM is needed for intent + language |
| **Voice** | Mic → `MediaRecorder` webm → `POST /api/stt` (Whisper) → `POST /api/chat` → `POST /api/tts` (Orpheus wav) → `<audio>` | `services/` | Voice is I/O, not agent logic |
| **History** | `History → Search Patna → 7/14/30 Days ← Previous` → Timeline `17 Sept 32° ERA5-Land` + `20 Sept 33° GFS` + Chart `MAX/MIN` → click day → hourly | `history/providers/open_meteo.py` (`archive-api` for `<today`, `api.open-meteo` for `>=today`) → `history/service.py` merge + `type` tag | No DB — data already remote; transparency via `type/source` |
| **Alerts** | `Alerts → Type Patna → Enable` → leave site → `🔔` when `Patna` has Orange warning | `IMD → worker → MongoDB → WebPush` | Event-driven, not conversation-driven (LLM would waste calls every 15 min) |
| **Study Hub** | `Study → Learn the Weather → Thunderstorms 3 lessons → Why does warm air rise? → Explain simply (Groq teacher) → Quiz 5 Q → Almost → Why? → Next → 4/5 Nice work → Worth reviewing → Practice again (new LLM question)` | `study_hub/content/topics.json` (trusted) + `study_hub/router.py` (`/explain` = teacher, not fact source) | Content is controlled, feedback explains *why* (supportive, not `Wrong`) |

Integrated product: `WeatherGPT → Study → Learn why heavy rain happens` from a forecast card or after an alert `Understand this warning`.

---

## Model Training — ipynb + pkl in `model/`

**Dataset ([Arko007/weathergpt-d1-mos-dataset](https://huggingface.co/datasets/Arko007/weathergpt-d1-mos-dataset)):**
```python
from datasets import load_dataset

ds = load_dataset("Arko007/weathergpt-d1-mos-dataset")
# ds["train"] contains GFS forecasts vs ground-truth observations
# across multiple Indian cities (lat/lon/elevation), each row is a
# forecast hour with: GFS temperature, humidity, wind, lead_hours,
# coordinates, elevation, UTC hour, month, valid_time, truth_temperature
```

The dataset pairs **GFS forecast runs** with **ground-truth observations** (Open-Meteo D1-MOS archive). Each sample has the 9 input features the model uses: `fc_temperature_2m_gfs_seamless`, `fc_relative_humidity_2m_gfs_seamless`, `fc_wind_speed_10m_gfs_seamless`, `lead_hours`, `lat`, `lon`, `elevation_m`, `hour_utc`, `month`. The label is `temperature_error = truth - GFS`, which the XGBoost model learns to predict.

**Files (`model/`):**
- `model/weathergpt_temperature_xgb.pkl` — **56 KB** XGBoost regressor that predicts `error = corrected - GFS`. Loaded in `inference.py:7` `pickle.load` → `model.predict(model_input)` → `corrected = GFS + predicted_error`.
- `model/weathergpt_temperature_bias_correction_ipynb.ipynb` — full training code (Colab T4). Steps: `load_dataset("Arko007/weathergpt-d1-mos-dataset")` → select features → compute `temperature_error = truth - GFS` → time-based train/val/test split (70/15/15) → `XGBRegressor` `n_estimators=500, max_depth=8, learning_rate=0.05` → export `weathergpt_temperature_xgb.pkl`.

**Input to model (`inference.py:152`):**
```python
np.array([[gfs_temperature, relative_humidity, wind_speed,
           lead_hours, latitude, longitude, elevation,
           hour_utc, month]], dtype=np.float32)
```

**Keep it on GitHub?** `*.pkl` is tiny, so simple is to `git add model/weathergpt_temperature_xgb.pkl` (works with `inference.py:7`). The dataset lives on HuggingFace (`Arko007/weathergpt-d1-mos-dataset`), not in the repo. For larger future models, switch to `Git LFS` or host on HuggingFace and `curl` on deploy. The `*.ipynb` is **not needed at runtime** — keep it for reproducibility, but don't load it.

Re-train: Open the `ipynb` in Colab, run all, download new `.pkl` to `model/` and restart `uvicorn`.

---

## Quick Start

```bash
git clone WeatherGpt
cd WeatherGpt
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\activate
pip install -r requirements.txt  # groq, langchain-groq, langgraph, fastapi, uvicorn, pymongo, pywebpush, apscheduler, python-dotenv, xgboost<3.0, etc.

cp .env.example .env  # then edit .env (see below)
# set GROQ_API_KEY from https://console.groq.com/keys
# set MONGODB_URI from Atlas, VAPID keys via: python -c "from py_vapid import Vapid; v=Vapid(); v.generate_keys(); print(v.public_key)"
uvicorn main:app --reload --port 8000
# open http://localhost:8000/          → Landing → Launch App → /chat
#       http://localhost:8000/history.html
#       http://localhost:8000/alerts.html
#       http://localhost:8000/study.html
```

**CLI preview (no UI):**
```bash
python app.py "What is weather tomorrow in Kolkata?" --voice  # also writes output.wav
```

**Docker (optional):**
```dockerfile
FROM python:3.11
COPY . .
RUN pip install -r requirements.txt
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Environment Variables

See `.env.example` (template, never commit real `.env`). Required:

| Key | Where to get | Used in |
|---|---|---|
| `GROQ_API_KEY` | `https://console.groq.com/keys` → `gsk_...` | `agent/graph.py:17` `ChatGroq`, `study_hub/router.py:35` `explain`, `services/stt.py` `tts.py` |
| `MONGODB_URI` | Atlas `mongodb+srv://user:pass@cluster...` | `alerts/db.py:1` |
| `MONGODB_DB` | optional, default `weathergpt` | `alerts/db.py:1` |
| `VAPID_PUBLIC_KEY` | `python -c "from py_vapid import Vapid; v=Vapid(); v.generate_keys(); print..."` `87` chars | `ui/alerts.html:81` `subscribe`, `main.py:159` `GET /api/alerts/vapid-public-key` |
| `VAPID_PRIVATE_KEY` | same generation, `43` chars, keep secret | `alerts/push.py:5` `webpush` |
| `VAPID_SUBJECT` | `mailto:alerts@weathergpt.local` | `alerts/push.py:5` `vapid_claims` |
| `ALERT_POLL_INTERVAL_MIN` | default `15`, tune after IMD `issued_at` cadence | `alerts/worker.py:10` |

IMD mock: `MOCK_ALERTS=1` (only for local demo while `401`).

---

## API Reference

**AI Agent:**
```http
POST /api/chat {query: "Kal Patna me mausam kaisa rahega?"}
→ {reply:"Kal Patna me 32.5°C...", lang:"hinglish", weather:{temperature:32.5,humidity:49,wind:5.2}, query:"..."}
POST /api/stt  multipart file: audio.webm → {text:"Kal Patna me mausam..."}
POST /api/tts  {text:"...", lang:"en|hinglish"} → audio/wav
POST /api/voice multipart file → audio/wav + headers X-Transcript, X-Reply
GET  /chat → ui/chat.html (after landing)
```

**History (no DB):**
```http
GET /api/history/locations?q=Patna → {locations:[{name:"Patna",latitude:25.59,longitude:85.13,country:"India",timezone:"Asia/Kolkata"}]}
GET /api/history?latitude=25.59&longitude=85.13&start_date=2026-09-17&end_date=2026-09-23&name=Patna
→ {location:{...}, days:[{date:"2026-09-17",type:"historical",source:"ERA5-Land",temperature_max:31.9,...},{date:"2026-09-20",type:"forecast",source:"GFS + WeatherGPT ML correction",...}]}
GET /api/history/day?latitude=..&longitude=..&date=2026-09-20 → {location, date, type, source, daily:{temperature_2m_max,...}, hourly:[{time,temperature_2m,...}]}
```

**Alerts (MongoDB + Web Push):**
```http
POST /api/alerts/subscribe {location_name:"Patna",district_id:573,state:"Bihar",push_subscription:{endpoint:"https://fcm...",keys:{p256dh:"...",auth:"..."}},alerts_enabled:true}
GET  /api/alerts/vapid-public-key → {publicKey:"BHFlL..."}
GET  /api/alerts/stats → {unique_districts:[573], total:2}
POST /api/alerts/unsubscribe {endpoint:"https://fcm..."}
GET  /health → {status:"ok"}
```
`GET /api/alerts/debug` and `POST /api/alerts/test` exist only if `MOCK_ALERTS=1` (removed in production build).

**Study Hub:**
```http
GET /api/study/topics → {topics:[{id:"thunderstorms",title:"Thunderstorms",lessons:[...],quiz:[...]}, ...]}
GET /api/study/topic/thunderstorms
GET /api/study/quiz/thunderstorms
POST /api/study/explain {topic_id, question, mode:"simple"} → {answer:"Warm air is less dense..."}
POST /api/study/quiz/submit {topic_id, answers:{t1:0}} → {total:5, correct:4, details:[{id, selected, correct, is_correct, why}]}
POST /api/study/quiz/practice-again {topic_id, question} → {question:{text,options,correct,why}}
```

---

## Running the Alert Worker

Worker is started automatically on `uvicorn` (`main.py:on_startup` → `alerts/worker.py:start_scheduler()`). It logs:

```
[MAIN] Alert worker scheduled every 15 min
[WORKER] unique districts from DB (filtered >0): [573]
[IMD DISTRICT] id=573 -> 200 len=...
[WORKER] finished {'checked':1,'new':1,'mode':'district',...}
```

Manual run: `python -m alerts.worker` or `curl -X POST http://localhost:8000/api/alerts/debug` (only with `MOCK_ALERTS=1`).

Notification click: `ui/sw.js:1` `push` → `showNotification(🚨 Orange Alert — Patna, Heavy rain..., icon:/weathergpt.png, vibrate, requireInteraction, actions:[View in WeatherGPT,Dismiss])` → `notificationclick` → `clients.openWindow("/history.html?q=Patna")` (history auto-selects `Patna, Bihar` without showing world `Patna Scotland` chips).

---

## Model Details — `model/weathergpt_temperature_bias_correction_ipynb.ipynb`

It contains:

1.  **Data:** `load_dataset("Arko007/weathergpt-d1-mos-dataset")` — 127 parquet files from Open-Meteo D1-MOS GFS archive vs ground-truth observations across Indian cities. Columns: `fc_temperature_2m_gfs_seamless`, `fc_relative_humidity_2m_gfs_seamless`, `fc_wind_speed_10m_gfs_seamless`, `lead_hours`, `lat`, `lon`, `elevation_m`, `hour_utc`, `month`, `valid_time`, `truth_temperature_2m`.
2.  **Label:** `temperature_error = truth_temperature_2m - fc_temperature_2m_gfs_seamless` (model predicts the GFS bias, not absolute temperature).
3.  **Split:** Time-based 70/15/15 (train/val/test) — no data leakage from future into training.
4.  **Train:** `XGBRegressor` `n_estimators=500, max_depth=8, learning_rate=0.05, subsample=0.8, colsample_bytree=0.8, objective="reg:squarederror"`, evaluate MAE vs raw GFS, export `weathergpt_temperature_xgb.pkl`.
5.  **Inference (`inference.py:7`):** `pickle.load` → `model.predict` on 9 features → `corrected = gfs_temperature + predicted_error`.

To re-train, open the `ipynb` in Colab (T4), `Runtime → Run all`, download the new `.pkl` to `model/` and commit (small) or use `Git LFS` if larger.

---

## Legal / IMD

IMD warnings are official. Do not fabricate warnings. The polished `🚨 Orange Alert` text in `alerts/worker.py:51` + `push.py:17` comes only from `IMD_CAP` or `District API` `Day1-4` codes after whitelisting. For fallback `Mock` in local dev, keep `MOCK_ALERTS=1` separate from production.

---

## License

MIT — see `LICENSE` (add one). Model `*.pkl` is derived from GFS + your training, keep it versioned with the `ipynb`.
