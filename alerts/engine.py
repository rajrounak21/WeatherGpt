"""
Alert engine — normalize → dedup → match subscriptions.
Worker calls this, NOT the LLM.
"""

import hashlib

def normalize_warning(raw_item: dict) -> dict:
    """
    Convert IMD raw (district_api or cap) into internal format:
    {warning_id, district_id, severity, event, valid_from, valid_until, raw_hash}
    Phase 0 locks the mapping from IMD codes to severity/event.
    """
    district_id = raw_item.get("district_id")
    cap_id = raw_item.get("cap_id")
    raw = raw_item.get("raw", {})
    raw_hash = raw_item.get("raw_hash") or hashlib.sha256(str(raw).encode()).hexdigest()[:16]

    # CAP path: if cap_id exists, use it as warning_id
    if cap_id:
        return {
            "warning_id": str(cap_id),
            "district_id": district_id,  # may be derived from areaDesc later
            "severity": str(raw.get("severity") or raw.get("level") or "unknown").lower(),
            "event": str(raw.get("event") or "unknown").lower(),
            "valid_from": raw.get("effective") or raw.get("onset"),
            "valid_until": raw.get("expires") or raw.get("valid_until"),
            "raw_hash": raw_hash,
        }
    # District API path: no stable id -> hash district+raw
    warning_id = raw_item.get("warning_id") or f"{district_id}:{raw_hash}"
    # TODO: map Day1-4 codes to severity/event after Phase 0
    return {
        "warning_id": warning_id,
        "district_id": district_id,
        "severity": "unknown",
        "event": "unknown",
        "valid_from": None,
        "valid_until": None,
        "raw_hash": raw_hash,
    }

def is_new_warning(db, warning: dict) -> bool:
    """Check processed_warnings collection for dedup."""
    if db is None or db[1] is None:
        return True
    _, proc = db
    try:
        exists = proc.find_one({"_id": warning["warning_id"]})
        return exists is None
    except Exception:
        return True

def mark_processed(db, warning: dict):
    if db is None or db[1] is None:
        return
    _, proc = db
    try:
        proc.insert_one({"_id": warning["warning_id"], **warning})
    except Exception:
        pass
