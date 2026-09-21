"""
Background worker — NOT triggered by user, runs every ALERT_POLL_INTERVAL_MIN.
"""

import os
from dotenv import load_dotenv

load_dotenv(override=True)

POLL_MIN = int(os.getenv("ALERT_POLL_INTERVAL_MIN", "15"))

def get_unique_districts(db):
    if db is None or db[0] is None:
        return []
    subs, _ = db
    try:
        ids = subs.distinct("district_id", {"alerts_enabled": True})
        return [i for i in ids if isinstance(i, int) and i > 0]
    except Exception:
        return []

def run_once():
    from alerts.db import get_collections, ensure_indexes
    from alerts.providers.imd import fetch_district_warnings, fetch_cap_alerts
    from alerts.engine import normalize_warning, is_new_warning, mark_processed
    from alerts.push import find_subscriptions, send_web_push

    db = get_collections()
    ensure_indexes()

    cap_items = fetch_cap_alerts()
    if cap_items:
        raw_items = cap_items
        mode = "cap"
    else:
        district_ids = get_unique_districts(db)
        if not district_ids:
            return {"checked": 0, "new": 0, "mode": "district", "unique_districts": []}
        raw_items = fetch_district_warnings(district_ids)
        mode = "district"

    new_count = 0
    for raw in raw_items:
        w = normalize_warning(raw)
        if not is_new_warning(db, w):
            continue
        subs = find_subscriptions(db, w.get("district_id")) if w.get("district_id") else []
        # premium warning style — siren + district name + urgency + interactive
        dname = w.get("location_name") or f"District {w.get('district_id') or 'Area'}"
        sev = (w.get("severity") or "orange").lower()
        sev_label = {"yellow":"Yellow","orange":"Orange","red":"Red"}.get(sev, sev.title())
        event = w.get("event") or "severe weather"
        title = f"🚨 {sev_label} Alert — {dname}"
        body = f"IMD {sev_label} warning: {event.replace('_',' ')} expected. Tap to see safety tips in WeatherGPT."
        # redirect to history where they see actual weather now (alerts has no data)
        # use location_name for history search (?q=Patna) — simple, history will geocode
        hist_city = (w.get("location_name") or dname).split("—")[0].strip().split(",")[0].strip()
        for s in subs:
            send_web_push(s.get("push_subscription") or s.get("subscription"), title, body, url=f"/history.html?q={hist_city}", severity=sev)
        mark_processed(db, w)
        new_count += 1

    return {"checked": len(raw_items), "new": new_count, "mode": mode, "unique_districts": get_unique_districts(db) if mode=="district" else []}

def start_scheduler():
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
    except ImportError:
        return None
    sched = BackgroundScheduler()
    sched.add_job(run_once, "interval", minutes=POLL_MIN, id="alert_poll", max_instances=1, coalesce=True)
    sched.start()
    return sched

if __name__ == "__main__":
    print(run_once())
