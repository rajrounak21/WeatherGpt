"""
IMD provider — NOT a LangGraph tool. Called only by worker.py.
District API: warnings_district_api.php?id=<district obj_id> -> Day1-4
"""

import hashlib
import requests

DISTRICT_API = "https://mausam.imd.gov.in/api/warnings_district_api.php"
CAP_API = "https://wis2box.imd.gov.in/oapi/collections/discovery-metadata/items"


def fetch_district_warnings(district_ids: list[int], timeout: int = 10) -> list[dict]:
    out = []
    for did in district_ids:
        try:
            r = requests.get(DISTRICT_API, params={"id": did}, timeout=timeout)
            if r.status_code != 200:
                continue
            data = r.json() if "json" in r.headers.get("content-type","") else {"raw": r.text}
            raw_hash = hashlib.sha256(r.text.encode()).hexdigest()[:16]
            out.append({"district_id": did, "raw": data, "raw_hash": raw_hash, "source": "district_api"})
        except Exception:
            continue
    return out


def fetch_cap_alerts(timeout: int = 10) -> list[dict]:
    try:
        r = requests.get(CAP_API, params={"f": "json", "limit": 20}, timeout=timeout)
        if r.status_code != 200:
            return []
        j = r.json()
        features = j.get("features", []) if isinstance(j, dict) else []
        out = []
        for f in features:
            props = f.get("properties", f)
            if not any(k in props for k in ("severity","event","areaDesc","effective","expires")):
                continue
            out.append({"raw": props, "source": "cap", "cap_id": props.get("id") or props.get("identifier")})
        return out
    except Exception:
        return []
