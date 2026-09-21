"""
Web Push — called by engine after new warning matched to district.
"""

def send_web_push(subscription: dict, title: str, body: str, url: str = "/", severity: str = "orange") -> bool:
    """
    Send via pywebpush — premium warning style with siren.
    """
    try:
        import os
        import json
        from pywebpush import webpush, WebPushException
        vapid_private = os.getenv("VAPID_PRIVATE_KEY", "").strip()
        vapid_claims = {"sub": os.getenv("VAPID_SUBJECT", "mailto:alerts@weathergpt.local")}
        if not vapid_private:
            return False
        payload = json.dumps({
            "title": title,
            "body": body,
            "url": url,
            "severity": severity,
            "icon": "/weathergpt.png",
            "badge": "/weathergpt.png",
            "vibrate": [200, 100, 200],
            "requireInteraction": True,
            "actions": [{"action":"open","title":"View in WeatherGPT"}, {"action":"dismiss","title":"Dismiss"}]
        })
        webpush(
            subscription_info=subscription,
            data=payload,
            vapid_private_key=vapid_private,
            vapid_claims=vapid_claims,
        )
        return True
    except Exception as e:
        return False

def find_subscriptions(db, district_id: int):
    if db is None or db[0] is None:
        return []
    subs, _ = db
    try:
        return list(subs.find({"district_id": district_id, "alerts_enabled": True}))
    except Exception:
        return []
