"""MongoDB connection — Phase 0/1: uses MONGODB_URI, district_id as key"""
import os
from dotenv import load_dotenv

load_dotenv(override=True)

MONGODB_URI = os.getenv("MONGODB_URI", "").strip()
DB_NAME = os.getenv("MONGODB_DB", "weathergpt")

_client = None
_db = None

def get_db():
    global _client, _db
    if _db is not None:
        return _db
    if not MONGODB_URI:
        return None
    try:
        from pymongo import MongoClient
        _client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        _client.admin.command("ping")
        _db = _client[DB_NAME]
        return _db
    except Exception:
        return None

def get_collections():
    db = get_db()
    if db is None:
        return None, None
    return db["alert_subscriptions"], db["processed_warnings"]

def ensure_indexes():
    subs, proc = get_collections()
    if subs is None or proc is None:
        return
    try:
        subs.create_index("district_id")
        subs.create_index("alerts_enabled")
        proc.create_index("district_id")
        proc.create_index("valid_until")
    except Exception:
        pass
