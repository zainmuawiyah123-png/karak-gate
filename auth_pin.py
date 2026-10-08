"""PIN من 4 أرقام للزبائن والتجار والسائقين (جداول customers / merchants / drivers).
الأعمدة المطلوبة في كل جدول: pin_hash text, pin_fails int, locked_until text  (انظر supabase_update_2.sql)
تنبيه صريح: هذا يمنع الدخول العابر والتخمين، لكنه لا يغني عن تفعيل RLS لأن مفتاح anon موجود في الكود.
"""
import hashlib
import hmac
import re
from datetime import datetime, timedelta

import streamlit as st

MAX_FAILS = 5
LOCK_MINUTES = 15
NO_PIN = "no_pin"


def _salt():
    try:
        return str(st.secrets["PIN_SALT"])
    except Exception:
        return "karak-gate-v1"


def valid_pin(pin):
    return bool(re.fullmatch(r"\d{4}", str(pin or "")))


def norm_phone(p):
    """يوحّد الرقم إلى الشكل المحلي 07XXXXXXXX إن أمكن."""
    d = re.sub(r"\D", "", str(p or ""))
    if d.startswith("00"):
        d = d[2:]
    if d.startswith("962"):
        d = "0" + d[3:]
    if len(d) == 9 and d.startswith("7"):
        d = "0" + d
    return d


def valid_phone(p):
    return bool(re.fullmatch(r"07\d{8}", norm_phone(p)))


def hash_pin(table, row_id, pin):
    """الملح = اسم الجدول + رقم السجل، فتغيير رقم الهاتف لاحقًا لا يُبطل الـ PIN."""
    return hashlib.pbkdf2_hmac("sha256", str(pin).encode(), f"{_salt()}:{table}:{row_id}".encode(), 60000).hex()


def set_pin(sb, table, row_id, phone, pin):
    """phone غير مستخدم (متروك للتوافق)."""
    sb.table(table).update({"pin_hash": hash_pin(table, row_id, pin), "pin_fails": 0, "locked_until": None}).eq("id", row_id).execute()


def find_by_phone(sb, table, phone):
    """يبحث بالرقم الموحّد ثم بالرقم كما كُتب (للسجلات القديمة)."""
    for p in dict.fromkeys([norm_phone(phone), str(phone or "").strip()]):
        if not p:
            continue
        rows = sb.table(table).select("*").eq("phone", p).limit(1).execute().data or []
        if rows:
            return rows[0]
    return None


def check_pin(sb, table, row, pin):
    """يرجع (نجح؟، رسالة). الرسالة NO_PIN إن كان الحساب بلا PIN."""
    now = datetime.now()
    lu = row.get("locked_until")
    if lu:
        try:
            if datetime.fromisoformat(str(lu)) > now:
                return False, "الحساب مقفل مؤقتًا بسبب محاولات خاطئة، حاول بعد قليل."
        except ValueError:
            pass
    if not row.get("pin_hash"):
        return False, NO_PIN
    if hmac.compare_digest(hash_pin(table, row["id"], pin), str(row["pin_hash"])):
        if row.get("pin_fails"):
            try:
                sb.table(table).update({"pin_fails": 0, "locked_until": None}).eq("id", row["id"]).execute()
            except Exception:
                pass
        return True, ""
    fails = int(row.get("pin_fails") or 0) + 1
    upd = {"pin_fails": fails}
    if fails >= MAX_FAILS:
        upd = {"pin_fails": 0, "locked_until": (now + timedelta(minutes=LOCK_MINUTES)).isoformat()}
    try:
        sb.table(table).update(upd).eq("id", row["id"]).execute()
    except Exception:
        pass
    return False, "رقم PIN غير صحيح."
