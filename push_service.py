"""إشعارات Web Push مجانية على Supabase.   pip: pywebpush"""
import base64
import json

from pywebpush import webpush, WebPushException
from db import get_sb, _secret


def decode_sub(b64_text):
    pad = "=" * (-len(b64_text) % 4)
    return json.loads(base64.urlsafe_b64decode(b64_text + pad).decode())


def save_subscription(role, owner_key, sub: dict):
    get_sb().table("push_subs").upsert(
        {"role": role, "owner_key": str(owner_key),
         "endpoint": sub["endpoint"], "sub_json": sub},
        on_conflict="endpoint",
    ).execute()


def send_push(role, owner_key, title, body, url="/"):
    """يرجع عدد الأجهزة التي وصلها الإشعار (0 = المستلم لم يفعّل الإشعارات)."""
    sb = get_sb()
    rows = (sb.table("push_subs").select("id, sub_json")
            .eq("role", role).eq("owner_key", str(owner_key)).execute().data or [])
    payload = json.dumps({"title": title, "body": body, "url": url}, ensure_ascii=False)
    sent = 0
    for r in rows:
        try:
            webpush(
                subscription_info=r["sub_json"],
                data=payload,
                vapid_private_key=_secret("VAPID_PRIVATE_KEY"),
                vapid_claims={"sub": _secret("VAPID_EMAIL", "mailto:admin@example.com")},
                ttl=3600,
            )
            sent += 1
        except WebPushException as e:
            if getattr(e.response, "status_code", None) in (404, 410):
                sb.table("push_subs").delete().eq("id", r["id"]).execute()
        except Exception:
            pass
    return sent
