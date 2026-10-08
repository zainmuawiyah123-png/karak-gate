"""أجرة التوصيل - متوافقة مع تطبيقك: الأجرة الأساسية delivery_fee + fee_per_km لكل كم (في جدول merchants)."""
import re

DEFAULT_PER_KM = 0.25   # دينار لكل كم عندما لا تحدد الإدارة سعرًا خاصًا للمتجر (fee_per_km فارغ)
DEFAULT_BASE_FEE = 1.50


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
    base = DEFAULT_BASE_FEE if base is None else float(base)
    per_km = merchant.get("fee_per_km")
    per_km = DEFAULT_PER_KM if per_km is None else float(per_km)   # 0 = أجرة ثابتة عمدًا
    return round(base + per_km * km, 2)
