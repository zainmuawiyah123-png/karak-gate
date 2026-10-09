import hashlib
import hmac
import os
import re

NO_PIN = "NO_PIN"


def norm_phone(phone):
    value = re.sub(r"\D", "", str(phone or ""))
    if value.startswith("962") and len(value) == 12:
        value = "0" + value[3:]
    return value


def valid_phone(phone):
    return bool(re.fullmatch(r"07\d{8}", norm_phone(phone)))


def valid_pin(pin):
    return bool(re.fullmatch(r"\d{4}", str(pin or "")))


def _hash_pin(pin):
    salt = os.urandom(16).hex()
    iterations = 210000
    digest = hashlib.pbkdf2_hmac(
        "sha256", str(pin).encode("utf-8"), bytes.fromhex(salt), iterations
    ).hex()
    return f"pbkdf2_sha256${iterations}${salt}${digest}"


def _verify_pin(pin, stored):
    stored = str(stored or "")
    if not stored:
        return False
    # دعم صيغة PBKDF2 التي ينشئها هذا الملف.
    parts = stored.split("$")
    if len(parts) == 4 and parts[0] == "pbkdf2_sha256":
        try:
            iterations = int(parts[1])
            digest = hashlib.pbkdf2_hmac(
                "sha256", str(pin).encode("utf-8"), bytes.fromhex(parts[2]), iterations
            ).hex()
            return hmac.compare_digest(digest, parts[3])
        except Exception:
            return False
    # دعم bcrypt إذا كانت القيمة القديمة بصيغة bcrypt.
    if stored.startswith(("$2a$", "$2b$", "$2y$")):
        try:
            import bcrypt
            return bool(bcrypt.checkpw(str(pin).encode("utf-8"), stored.encode("utf-8")))
        except Exception:
            return False
    # توافق احتياطي مع الحسابات القديمة التي خزنت PIN كنص صريح.
    return hmac.compare_digest(stored, str(pin))


def find_by_phone(sb, table, phone):
    normalized = norm_phone(phone)
    try:
        result = sb.table(table).select("*").eq("phone", normalized).limit(1).execute()
        return (result.data or [None])[0]
    except Exception:
        return None


def set_pin(sb, table, row_id, phone, pin):
    if not valid_pin(pin):
        raise ValueError("PIN must contain exactly 4 digits")
    payload = {"phone": norm_phone(phone), "pin_hash": _hash_pin(pin)}
    return sb.table(table).update(payload).eq("id", row_id).execute()


def check_pin(sb, table, row, pin):
    if not row:
        return False, "الحساب غير موجود"
    stored = row.get("pin_hash")
    if not stored:
        return False, NO_PIN
    if not valid_pin(pin):
        return False, "رمز PIN غير صحيح"
    if _verify_pin(pin, stored):
        return True, "OK"
    return False, "رمز PIN غير صحيح"
