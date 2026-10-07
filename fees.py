"""أجرة التوصيل - متوافقة مع تطبيقك: الأجرة الأساسية delivery_fee + fee_per_km لكل كم (في جدول merchants)."""
import re


def order_delivery_fee(order):
    """الأجرة التي سجّلها تطبيق الزبون داخل تفاصيل الطلب (سطر 'التوصيل: 1.75'). None إن لم توجد."""
    m = re.search(r"التوصيل:\s*([\d.]+)", str(order.get("order_details") or ""))
    try:
        return float(m.group(1)) if m else None
    except ValueError:
        return None


def merchant_fee(merchant, km):
    """أجرة المتجر حسب المسافة: الأساسية + (سعر الكم × المسافة)."""
    base = merchant.get("delivery_fee")
    base = 1.50 if base is None else float(base)
    per_km = float(merchant.get("fee_per_km") or 0)
    return round(base + per_km * km, 2)
