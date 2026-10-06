import sys
import io
import base64
from datetime import datetime
import re
import math
from urllib.parse import quote, unquote

import streamlit as st
from supabase import create_client


# ============================================================
# إعداد UTF-8
# ============================================================
try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")
except Exception:
    pass


# ============================================================
# إعداد Supabase
# ============================================================
SUPABASE_URL = "https://tzkdxodvlzggmcntnqer.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InR6a2R4b2R2bHpnZ21jbnRucWVyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTA5MzM3MzksImV4cCI6MjEwNjUwOTczOX0.M944yHglTXVyPrxySSQj0MBaqpr2I_8ub7Uoofbd2_4"

try:
    if "SUPABASE_ANON_KEY" in st.secrets:
        SUPABASE_ANON_KEY = str(st.secrets["SUPABASE_ANON_KEY"]).strip()
except Exception:
    pass


WHATSAPP_NUMBER = "962797088219"  # +962797088219

DEFAULT_DELIVERY_FEE = 1.50   # الأجرة الافتراضية إذا لم تحددها الإدارة للمتجر
MIN_ORDER_VALUE = 5.0          # الحد الأدنى لقيمة الأصناف (بدون التوصيل والخدمة)
ROAD_FACTOR = 1.3             # معامل تقريبي لتحويل المسافة المباشرة إلى مسافة طريق

# ============================================================
# إعدادات العروض التسويقية (عدّلها كما تريد)
# ============================================================
PROMO_BANNERS = [
    {"title": "خصم 20% على أول طلب", "sub": "للعملاء الجدد في الكرك", "tag": "عرض الترحيب", "bg": "linear-gradient(135deg,#7B1FD6,#A24BF0)"},
    {"title": "توصيل سريع لباب بيتك", "sub": "من متاجر الكرك المعتمدة", "tag": "توصيل سريع", "bg": "linear-gradient(135deg,#FF5A00,#FF8A3D)"},
    {"title": "اطلب من أكثر من متجر", "sub": "سلة واحدة وفاتورة واحدة", "tag": "جديد", "bg": "linear-gradient(135deg,#5B14A8,#8A2BE2)"},
]


# ============================================================
# إعداد الصفحة
# ============================================================
st.set_page_config(
    page_title="بوابة الكرك - Karak Gate",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="collapsed"
)


# ============================================================
# CSS
# ============================================================
st.markdown(
    """
<style>
#MainMenu, .stDeployButton, header, footer {
    visibility: hidden;
    display: none;
}
.stApp {
    background: #FFFFFF !important;
    color: #2D3142 !important;
}
.block-container {
    padding-top: 0.6rem !important;
    padding-bottom: 3rem !important;
    max-width: 1400px !important;
}
h1, h2, h3, h4, h5, h6, p, label, span {
    color: #2D3142 !important;
}

/* ---------- الأزرار ---------- */
div[data-testid="column"] .stButton > button {
    background: #FF5A00 !important;
    color: #FFFFFF !important;
    border-radius: 24px !important;
    border: 0 !important;
    font-weight: bold !important;
    font-size: 13px !important;
    padding: 6px 12px !important;
    min-height: 38px !important;
    margin: 4px auto 0 auto !important;
    display: block !important;
    width: 100% !important;
    transition: all 0.2s ease;
}
div[data-testid="column"] .stButton > button:hover {
    background: #E04E00 !important;
    transform: translateY(-1px);
}
.stButton > button {
    border-radius: 24px !important;
}

/* ---------- حقول الإدخال ---------- */
.stTextInput input, .stTextArea textarea {
    border-radius: 24px !important;
    border: 1.5px solid #E5DDF3 !important;
    background: #F7F3FC !important;
    padding: 10px 16px !important;
}
.stTextInput input:focus, .stTextArea textarea:focus {
    border-color: #7B1FD6 !important;
    box-shadow: 0 0 0 2px rgba(123,31,214,0.15) !important;
}

/* ---------- الهيدر البنفسجي ---------- */
.kg-header {
    background: linear-gradient(135deg, #6A12C4, #8A2BE2);
    border-radius: 0 0 28px 28px;
    padding: 16px 20px 22px 20px;
    margin: 0 0 15px 0;
    box-shadow: 0 6px 20px rgba(106,18,196,0.25);
}
.kg-header-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
}
.kg-deliver-label {
    color: #E9D8FF !important;
    font-size: 12px;
    margin: 0;
}
.kg-deliver-addr {
    color: #FFFFFF !important;
    font-size: 16px;
    font-weight: 800;
    margin: 0;
}
.kg-header-title {
    color: white !important;
    font-size: 22px;
    font-weight: 800;
    margin: 0;
}
.kg-header-sub {
    color: white !important;
    font-size: 12px;
    margin: 2px 0 0 0;
    opacity: 0.92;
}
.kg-bag {
    position: relative;
    background: #FFFFFF;
    width: 46px;
    height: 46px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 22px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.15);
}
.kg-bag-badge {
    position: absolute;
    top: -4px;
    right: -4px;
    background: #FF5A00;
    color: #FFFFFF !important;
    font-size: 11px;
    font-weight: 800;
    min-width: 20px;
    height: 20px;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    border: 2px solid #FFFFFF;
}
.kg-bag-badge span { color: #FFFFFF !important; }

/* ---------- بانرات العروض ---------- */
.kg-promo-scroll {
    display: flex;
    gap: 12px;
    overflow-x: auto;
    padding: 4px 2px 12px 2px;
    margin-bottom: 8px;
}
.kg-promo-card {
    min-width: 270px;
    border-radius: 18px;
    padding: 16px 18px;
    box-shadow: 0 4px 14px rgba(0,0,0,0.12);
    flex: 0 0 auto;
}
.kg-promo-tag {
    display: inline-block;
    background: #D7FF3B;
    color: #1B1B1B !important;
    font-size: 11px;
    font-weight: 800;
    padding: 3px 10px;
    border-radius: 12px;
    margin-bottom: 8px;
}
.kg-promo-tag span { color: #1B1B1B !important; }
.kg-promo-title {
    color: #FFFFFF !important;
    font-size: 18px;
    font-weight: 900;
    margin: 0;
}
.kg-promo-sub {
    color: #FFFFFF !important;
    font-size: 12px;
    margin: 4px 0 0 0;
    opacity: 0.95;
}

/* ---------- عناوين الأقسام ---------- */
.kg-section-title {
    font-size: 20px;
    font-weight: 900;
    color: #2D3142 !important;
    margin: 14px 0 8px 0;
}

/* ---------- المتاجر ---------- */
.kg-store-card {
    background: white;
    border-radius: 18px;
    padding: 12px;
    margin-bottom: 12px;
    border: 1px solid #ECE6F5;
    box-shadow: 0 3px 12px rgba(0,0,0,0.04);
    transition: all 0.25s ease;
}
.kg-store-card:hover {
    border-color: #7B1FD6;
    box-shadow: 0 6px 20px rgba(123,31,214,0.15);
}
.kg-store-name {
    font-size: 17px;
    font-weight: 900;
    margin: 2px 0 4px 0;
    color: #2D3142 !important;
}
.kg-chip {
    display: inline-block;
    background: #F3EAFD;
    color: #6A12C4 !important;
    font-size: 11px;
    font-weight: 700;
    padding: 3px 10px;
    border-radius: 12px;
    margin: 2px 4px 2px 0;
}
.kg-chip span { color: #6A12C4 !important; }
.kg-chip-green {
    background: #D7FF3B;
    color: #1B1B1B !important;
}
.kg-chip-green span { color: #1B1B1B !important; }
.kg-price {
    color: #FF5A00 !important;
    font-weight: 800;
    font-size: 15px;
}

/* ---------- السلة ---------- */
.kg-cart {
    background: #FBF8FF;
    border-radius: 20px;
    padding: 18px;
    border: 1px solid #E5DDF3;
    box-shadow: 0 4px 20px rgba(106,18,196,0.06);
}

/* ---------- زر واتساب ---------- */
[class*="st-key-submit_wa_"] button {
    background: #25D366 !important;
    color: #FFFFFF !important;
}

/* ---------- بطاقة القسم: إطار بحجم المحتوى (الحاسوب) ---------- */
.kg-cat-card {
    width: 112px !important;
    height: 106px !important;
    padding: 8px 4px 6px 4px !important;
    margin: 0 auto 6px auto !important;
    border-radius: 16px !important;
}
.kg-cat-card img {
    width: 56px !important;
    height: 56px !important;
    margin-bottom: 5px !important;
}
.kg-cat-name {
    font-size: 11px !important;
    line-height: 1.2 !important;
    white-space: normal !important;
    max-height: 26px;
    overflow: hidden;
}
div[data-testid="stHorizontalBlock"]:has(.kg-cat-card) .stButton {
    max-width: 112px;
    margin: 0 auto;
}

/* ---------- الأقسام على الهاتف: 4 في الصف وبطاقات مصغّرة ---------- */
@media (max-width: 640px) {
    div[data-testid="stHorizontalBlock"]:has(.kg-cat-card) {
        flex-wrap: wrap !important;
        gap: 6px !important;
    }
    div[data-testid="stHorizontalBlock"]:has(.kg-cat-card) > div {
        flex: 0 0 calc(25% - 6px) !important;
        width: calc(25% - 6px) !important;
        min-width: calc(25% - 6px) !important;
    }
    div[data-testid="stHorizontalBlock"]:has(.kg-cat-card) .stButton {
        max-width: 100%;
    }
    .kg-cat-card {
        width: 100% !important;
        height: 96px !important;
        padding: 8px 2px 6px 2px !important;
        border-radius: 14px !important;
        margin-bottom: 4px !important;
    }
    .kg-cat-card img {
        width: 46px !important;
        height: 46px !important;
        margin-bottom: 4px !important;
    }
    .kg-cat-name {
        font-size: 10px !important;
        line-height: 1.2 !important;
        white-space: normal !important;
        max-height: 24px;
        overflow: hidden;
    }
    div[data-testid="stHorizontalBlock"]:has(.kg-cat-card) .stButton > button {
        font-size: 10px !important;
        padding: 2px 0 !important;
        min-height: 26px !important;
        margin-top: 0 !important;
    }
}
</style>
""",
    unsafe_allow_html=True
)


# ============================================================
# الاتصال بـ Supabase
# ============================================================
def db():
    try:
        return create_client(SUPABASE_URL.strip(), SUPABASE_ANON_KEY.strip())
    except Exception as e:
        st.error(f"❌ تعذر الاتصال بـ Supabase: {e}")
        st.stop()

sb = db()


# ============================================================
# التحديث التلقائي
# ============================================================
try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=5000, key="customer_auto_refresh")
except Exception:
    pass


# ============================================================
# Session State
# ============================================================
if "phone" not in st.session_state:
    st.session_state.phone = ""

if "customer_name" not in st.session_state:
    st.session_state.customer_name = ""

if "customer_email" not in st.session_state:
    st.session_state.customer_email = ""

if "customer_address" not in st.session_state:
    st.session_state.customer_address = ""

if "delivery_notes" not in st.session_state:
    st.session_state.delivery_notes = ""

if "customer_map_link" not in st.session_state:
    st.session_state.customer_map_link = ""

if "cart" not in st.session_state:
    st.session_state.cart = []

if "nav_tab" not in st.session_state:
    st.session_state.nav_tab = "الرئيسية"

if "search_query" not in st.session_state:
    st.session_state.search_query = ""

if "search_input_key" not in st.session_state:
    st.session_state.search_input_key = 0

if "selected_merchant" not in st.session_state:
    st.session_state.selected_merchant = None

if "wa_pending_link" not in st.session_state:
    st.session_state.wa_pending_link = None

query_params = st.query_params
if "cat" in query_params:
    st.session_state.selected_category = query_params["cat"]
else:
    if "selected_category" not in st.session_state:
        st.session_state.selected_category = "الكل"


def normalize_map_link(value):
    v = str(value or "").strip()
    if v and not v.lower().startswith(("http://", "https://")):
        v = "https://" + v
    return v


def safe_price(value):
    try:
        return float(value or 0)
    except Exception:
        return 0.0


# ============================================================
# دالة رسم الهيدر على طراز تطبيقات التوصيل
# ============================================================
def flat_html(html):
    # يزيل الإزاحات والأسطر الفارغة حتى لا يعتبرها Markdown كتلة كود
    return "".join(line.strip() for line in html.splitlines() if line.strip())


def render_top_header(title, subtitle, show_deliver=True):
    cart_count = len(st.session_state.cart)
    addr_text = (st.session_state.customer_address or "").strip() or "حدّد عنوانك من صفحة حسابي"
    badge_html = f'<div class="kg-bag-badge"><span>{cart_count}</span></div>' if cart_count > 0 else ""
    if show_deliver:
        left_html = f"""
            <div>
                <div class="kg-deliver-label">التوصيل إلى</div>
                <div class="kg-deliver-addr">📍 {addr_text}</div>
            </div>
        """
    else:
        left_html = f"""
            <div>
                <div class="kg-header-title">{title}</div>
                <div class="kg-header-sub">{subtitle}</div>
            </div>
        """
    html = f"""
    <div class="kg-header">
        <div class="kg-header-row">
            {left_html}
            <div class="kg-bag">🛍{badge_html}</div>
        </div>
    """
    if show_deliver:
        html += f"""
        <div style="margin-top:10px;">
            <div class="kg-header-title">{title}</div>
            <div class="kg-header-sub">{subtitle}</div>
        </div>
        """
    html += "</div>"
    st.markdown(flat_html(html), unsafe_allow_html=True)


def render_promos():
    cards = ""
    for b in PROMO_BANNERS:
        cards += f"""
        <div class="kg-promo-card" style="background:{b['bg']};">
            <div class="kg-promo-tag"><span>{b['tag']}</span></div>
            <div class="kg-promo-title">{b['title']}</div>
            <div class="kg-promo-sub">{b['sub']}</div>
        </div>
        """
    st.markdown(flat_html(f'<div class="kg-promo-scroll">{cards}</div>'), unsafe_allow_html=True)


# ============================================================
# أجور التوصيل (تحددها الإدارة لكل متجر + المسافة)
# أعمدة اختيارية في جدول merchants:
#   delivery_fee  : الأجرة الأساسية للمتجر
#   fee_per_km    : أجرة إضافية لكل كم (0 = أجرة ثابتة)
#   lat, lng      : إحداثيات المتجر (وإلا تُستخرج من map_link)
# ============================================================
@st.cache_data(ttl=3600, show_spinner=False)
def resolve_map_url(url):
    url = str(url or "").strip()
    if not url:
        return ""
    if "goo.gl" in url or "maps.app" in url:
        try:
            import requests
            r = requests.get(url, allow_redirects=True, timeout=4)
            return r.url or url
        except Exception:
            return url
    return url


def extract_coords(url):
    u = unquote(resolve_map_url(url))
    patterns = [
        r"@(-?\d+\.\d+),(-?\d+\.\d+)",
        r"!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)",
        r"[?&](?:q|ll|query|destination|center)=(-?\d+\.\d+),\s*(-?\d+\.\d+)",
    ]
    for pat in patterns:
        m = re.search(pat, u)
        if m:
            lat, lng = float(m.group(1)), float(m.group(2))
            if -90 <= lat <= 90 and -180 <= lng <= 180:
                return (lat, lng)
    return None


def haversine_km(a, b):
    r = 6371.0
    la1, lo1, la2, lo2 = map(math.radians, [a[0], a[1], b[0], b[1]])
    d = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * r * math.asin(math.sqrt(d))


def merchant_coords(m):
    try:
        if m.get("lat") is not None and m.get("lng") is not None:
            return (float(m["lat"]), float(m["lng"]))
    except Exception:
        pass
    return extract_coords(m.get("map_link"))


def merchant_fee_info(m):
    base = m.get("delivery_fee")
    base = DEFAULT_DELIVERY_FEE if base in (None, "") else safe_price(base)
    per_km = safe_price(m.get("fee_per_km"))
    return base, per_km


def fee_label(m):
    base, per_km = merchant_fee_info(m)
    if per_km > 0:
        return f"🛵 توصيل من {base:.2f} د.أ"
    return f"🛵 توصيل {base:.2f} د.أ"


def compute_delivery(cart, merchants):
    by_name = {mm.get("name"): mm for mm in merchants}
    cust = extract_coords(st.session_state.customer_map_link) if st.session_state.customer_map_link else None
    total = 0.0
    lines = []
    uncertain = False
    for name in dict.fromkeys(item.get("merchant") for item in cart):
        m = by_name.get(name) or {}
        base, per_km = merchant_fee_info(m)
        fee = base
        dist = None
        store_xy = merchant_coords(m)
        if cust and store_xy:
            dist = haversine_km(cust, store_xy) * ROAD_FACTOR
            if per_km > 0:
                fee = base + per_km * dist
                fee = math.ceil(fee * 4) / 4  # تقريب لأقرب 0.25
        elif per_km > 0:
            uncertain = True
        total += fee
        lines.append((name, fee, dist))
    return total, lines, uncertain


def delivery_summary_line(delivery, lines):
    parts = [f"{name}: {dist:.1f} كم" for name, fee, dist in lines if dist is not None]
    extra = f" ({' | '.join(parts)})" if parts else ""
    return f"\n- التوصيل: {delivery:.2f} د.أ{extra}"


def render_min_order_notice(subtotal):
    if subtotal < MIN_ORDER_VALUE:
        st.warning(f"⚠️ الحد الأدنى للطلب {MIN_ORDER_VALUE:.2f} د.أ (بدون التوصيل والخدمة). يلزمك إضافة {MIN_ORDER_VALUE - subtotal:.2f} د.أ لإتمام الطلب.")


def render_delivery_details(lines, uncertain):
    for name, fee, dist in lines:
        extra = f" ({dist:.1f} كم تقريباً)" if dist is not None else ""
        st.caption(f"🛵 {name}: {fee:.2f} د.أ{extra}")
    if uncertain:
        st.caption("⚠️ تعذّر حساب المسافة (رابط موقعك أو موقع المتجر غير محدد)، فقد تؤكد الإدارة أجرة التوصيل النهائية.")


# ============================================================
# تنبيه الإدارة فقط عبر تيليجرام (اختياري، يحتاج TELEGRAM_BOT_TOKEN و TELEGRAM_CHAT_ID في st.secrets)
# ============================================================
def notify_admin_new_order(summary, total, payment):
    try:
        token = str(st.secrets["TELEGRAM_BOT_TOKEN"]).strip()
        chat_id = str(st.secrets["TELEGRAM_CHAT_ID"]).strip()
    except Exception:
        return
    if not token or not chat_id:
        return
    try:
        import requests
        text = (
            "🔔 طلب جديد - بوابة الكرك\n"
            f"الزبون: {st.session_state.customer_name} ({st.session_state.phone})\n"
            f"العنوان: {st.session_state.customer_address}\n"
            f"الموقع: {st.session_state.customer_map_link or '-'}\n"
            "----------------\n"
            f"{summary}\n"
            "----------------\n"
            f"الإجمالي: {total:.2f} د.أ | الدفع: {payment}"
        )
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data={"chat_id": chat_id, "text": text},
            timeout=5
        )
    except Exception:
        pass  # فشل التنبيه لا يجب أن يعطّل الطلب


# ============================================================
# دوال واتساب
# ============================================================
def build_whatsapp_link(summary, subtotal, delivery, service, total, payment):
    addr = (st.session_state.customer_address or "").strip() or "غير محدد"
    notes = (st.session_state.delivery_notes or "").strip() or "-"
    map_link = (st.session_state.customer_map_link or "").strip() or "-"
    msg = (
        "طلب جديد من تطبيق بوابة الكرك\n"
        f"الاسم: {st.session_state.customer_name}\n"
        f"الهاتف: {st.session_state.phone}\n"
        f"العنوان: {addr}\n"
        f"ملاحظات: {notes}\n"
        f"رابط الموقع: {map_link}\n"
        "----------------\n"
        f"{summary}\n"
        "----------------\n"
        f"مجموع الأصناف: {subtotal:.2f} د.أ\n"
        f"التوصيل: {delivery:.2f} د.أ\n"
        f"الخدمة: {service:.2f} د.أ\n"
        f"الإجمالي: {total:.2f} د.أ\n"
        f"طريقة الدفع: {payment}"
    )
    return f"https://wa.me/{WHATSAPP_NUMBER}?text={quote(msg)}"


def missing_fields():
    miss = []
    if not (st.session_state.customer_name or "").strip():
        miss.append("الاسم")
    if not (st.session_state.phone or "").strip():
        miss.append("رقم الهاتف")
    if not (st.session_state.customer_address or "").strip():
        miss.append("العنوان")
    return miss


def order_ready(subtotal=None):
    if subtotal is not None and subtotal < MIN_ORDER_VALUE:
        st.error(f"⚠️ لا يمكن إرسال الطلب: الحد الأدنى {MIN_ORDER_VALUE:.2f} د.أ (بدون التوصيل والخدمة)، ومجموع أصنافك {subtotal:.2f} د.أ.")
        return False
    miss = missing_fields()
    if miss:
        st.error("⚠️ يرجى إكمال بياناتك من صفحة «حسابي» قبل إرسال الطلب: " + "، ".join(miss))
        return False
    return True


def insert_order(summary, total, payment):
    sb.table("orders").insert({
        "customer_name": st.session_state.customer_name,
        "customer_phone": st.session_state.phone,
        "customer_address": f"{st.session_state.customer_address} (ملاحظات: {st.session_state.delivery_notes}) | رابط الخريطة: {st.session_state.customer_map_link}",
        "order_details": summary,
        "total_amount": total,
        "payment_method": payment,
        "order_status": "قيد التجهيز",
        "driver_name": "",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }).execute()
    notify_admin_new_order(summary, total, payment)


def render_whatsapp_option(summary, subtotal, delivery, service, total, payment, key_suffix="main"):
    miss = missing_fields()
    if miss:
        st.warning("⚠️ أكمل بياناتك من صفحة «حسابي» قبل الإرسال: " + "، ".join(miss))
    st.markdown(
        "<div style='text-align:center; font-size:12px; color:#64748B; margin:6px 0;'>— أو —</div>",
        unsafe_allow_html=True
    )
    if st.button("📲 تسجيل الطلب وإرساله عبر واتساب", key=f"submit_wa_{key_suffix}", use_container_width=True):
        if not order_ready(subtotal):
            return
        link = build_whatsapp_link(summary, subtotal, delivery, service, total, payment)
        try:
            insert_order(summary, total, payment)
        except Exception as e:
            st.error(f"خطأ أثناء إرسال الطلب: {e}")
            return
        st.session_state.wa_pending_link = link
        st.session_state.cart = []
        st.rerun()


# ============================================================
# دالة عرض الصور
# ============================================================
def display_image(value, width=100, fallback="🛒"):
    if not value:
        st.markdown(f"<span style='font-size:32px;'>{fallback}</span>", unsafe_allow_html=True)
        return

    val_str = str(value).strip()
    if val_str.startswith("http://") or val_str.startswith("https://") or val_str.startswith("data:image"):
        try:
            st.image(val_str, width=width)
            return
        except Exception:
            pass

    try:
        clean_hex = val_str.replace("\n", "").replace(" ", "")
        if len(clean_hex) >= 20 and len(clean_hex) % 2 == 0:
            raw = bytes.fromhex(clean_hex)
            st.image(raw, width=width)
            return
    except Exception:
        pass

    try:
        raw = base64.b64decode(val_str.strip(), validate=True)
        st.image(raw, width=width)
        return
    except Exception:
        pass

    st.markdown(f"<span style='font-size:32px;'>{fallback}</span>", unsafe_allow_html=True)


# ============================================================
# الأقسام
# ============================================================
categories = [
    {"name": "الكل", "image": "https://images.unsplash.com/photo-1504674900247-0877df9cc836?auto=format&fit=crop&w=300&q=80"},
    {"name": "مطاعم", "image": "https://images.unsplash.com/photo-1515003197210-e0cd71810b5f?auto=format&fit=crop&w=300&q=80"},
    {"name": "حلويات", "image": "https://images.unsplash.com/photo-1578985545062-69928b1d9587?auto=format&fit=crop&w=300&q=80"},
    {"name": "ماركت", "image": "https://images.unsplash.com/photo-1542838132-92c53300491e?auto=format&fit=crop&w=300&q=80"},
    {"name": "محامص ومكسرات", "image": "https://images.unsplash.com/photo-1599599810769-bcde5a160d32?auto=format&fit=crop&w=300&q=80"},
    {"name": "خضروات وفواكه", "image": "https://images.unsplash.com/photo-1619566636858-adf3ef46400b?auto=format&fit=crop&w=300&q=80"},
    {"name": "لحوم", "image": "https://images.unsplash.com/photo-1603048297172-c92544798d5a?auto=format&fit=crop&w=300&q=80"},
    {"name": "صيدليات ومستلزمات طبيه", "image": "https://images.unsplash.com/photo-1585435557343-3b092031a831?auto=format&fit=crop&w=300&q=80"}
]


# ============================================================
# التنقل العلوي
# ============================================================
nav_cols = st.columns(3)
with nav_cols[0]:
    if st.button("🏠 الرئيسية", use_container_width=True):
        st.session_state.nav_tab = "الرئيسية"
        st.session_state.selected_merchant = None
        st.session_state.search_query = ""
        st.session_state.search_input_key += 1
        st.rerun()
with nav_cols[1]:
    if st.button("📦 طلباتي والتتبع", use_container_width=True):
        st.session_state.nav_tab = "الطلبات"
        st.session_state.selected_merchant = None
        st.rerun()
with nav_cols[2]:
    if st.button("👤 حسابي", use_container_width=True):
        st.session_state.nav_tab = "الحساب"
        st.session_state.selected_merchant = None
        st.rerun()


# ============================================================
# 1. الرئيسية
# ============================================================
if st.session_state.nav_tab == "الرئيسية":

    render_top_header(
        "🛒 بوابة الكرك",
        "Karak Gate • اطلب ما تريد من متاجر الكرك بكل سهولة"
    )

    if st.session_state.wa_pending_link:
        st.success("🎉 تم تسجيل طلبك في النظام بنجاح! اضغط الزر الأخضر لإرسال تفاصيله إلى واتساب الإدارة.")
        st.markdown(
            f'<a href="{st.session_state.wa_pending_link}" target="_blank" style="display:block; text-align:center; background:#25D366; color:#FFFFFF !important; font-weight:bold; font-size:15px; padding:12px; border-radius:24px; text-decoration:none; margin:6px 0 10px 0;">📲 افتح واتساب وأرسل الرسالة للإدارة</a>',
            unsafe_allow_html=True
        )
        if st.button("✖ إخفاء هذه الرسالة", key="close_wa_pending"):
            st.session_state.wa_pending_link = None
            st.rerun()

    try:
        merchants_res = sb.table("merchants").select("*").execute()
        all_merchants = merchants_res.data if merchants_res.data else []
        
        products_res = sb.table("products").select("*").execute()
        all_products = products_res.data if products_res.data else []
    except Exception:
        all_merchants = []
        all_products = []

    if st.session_state.selected_merchant:
        mname = st.session_state.selected_merchant
        m_data = next((m for m in all_merchants if m.get("name") == mname), {"name": mname, "category": "", "location": "", "map_link": ""})
        
        if st.button("⬅ العودة إلى قائمة المتاجر والأقسام"):
            st.session_state.selected_merchant = None
            st.rerun()

        left_m, right_m = st.columns([2.2, 1], gap="large")

        with left_m:
            st.markdown(f"""
            <div style="background:linear-gradient(135deg,#F3EAFD,#FFFFFF); border-radius:20px; padding:20px; margin-bottom:15px; border:1px solid #E5DDF3; box-shadow:0 4px 15px rgba(106,18,196,0.08); display:flex; align-items:center; gap:15px;">
                <div>
                    <div style="font-size:24px; font-weight:900; color:#6A12C4;">🏬 {mname}</div>
                    <div style="margin-top:6px;">
                        <span class="kg-chip"><span>{m_data.get('category','')}</span></span>
                        <span class="kg-chip"><span>📍 {m_data.get('location','')}</span></span>
                        <span class="kg-chip kg-chip-green"><span>{fee_label(m_data)}</span></span>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            if m_data.get("map_link"):
                st.markdown(f'<a href="{normalize_map_link(m_data.get("map_link"))}" target="_blank" rel="noopener noreferrer" style="color:#6A12C4; font-weight:bold; text-decoration:none; display:inline-block; margin-bottom:15px;">🗺 فتح موقع المتجر على خرائط جوجل</a>', unsafe_allow_html=True)

            store_products = [p for p in all_products if p.get("merchant_name") == mname]

            if store_products:
                st.markdown(f'<div class="kg-section-title">📋 قائمة الأصناف المتوفرة ({len(store_products)} صنف)</div>', unsafe_allow_html=True)
                
                for pi, p in enumerate(store_products):
                    item_name = p.get("item_name", "صنف")
                    quantity = p.get("quantity", "")
                    unit = p.get("unit", "")
                    price = safe_price(p.get("price"))

                    p_col1, p_col2, p_col3 = st.columns([1.2, 3.8, 2])
                    
                    with p_col1:
                        display_image(p.get("image_path"), width=100, fallback="🍽")
                    
                    with p_col2:
                        st.markdown(f"<div style='font-size:16px; font-weight:bold; margin-top:5px;'>{item_name}</div>", unsafe_allow_html=True)
                        st.caption(f"{quantity} {unit} | <span class='kg-price'>{price:.2f} د.أ</span>", unsafe_allow_html=True)
                    
                    with p_col3:
                        st.markdown("<br>", unsafe_allow_html=True)
                        if st.button("➕ إضافة للسلة", key=f"add_store_p_{pi}_{p['id']}", use_container_width=True):
                            st.session_state.cart.append({
                                "name": f"{item_name} ({quantity} {unit})",
                                "price": price,
                                "merchant": mname
                            })
                            st.toast(f"تمت إضافة {item_name} إلى السلة!")
                    
                    st.markdown("<hr style='margin:10px 0; border:0; border-top:1px solid #F1ECF8;'>", unsafe_allow_html=True)
            else:
                st.info("لا توجد أصناف مضافة لهذا المتجر حتى الآن.")

        with right_m:
            st.markdown('<div class="kg-cart">', unsafe_allow_html=True)
            st.subheader("🛍 سلة الطلبات والفاتورة")

            if not st.session_state.cart:
                st.info("السلة فارغة حالياً.")
            else:
                subtotal = sum(safe_price(item.get("price")) for item in st.session_state.cart)

                for item in st.session_state.cart:
                    st.write(f"🔹 **{item['name']}**")
                    st.caption(f"{item['merchant']} | {item['price']:.2f} د.أ")

                delivery, delivery_lines, delivery_uncertain = compute_delivery(st.session_state.cart, all_merchants)
                service = 0.25
                total = subtotal + delivery + service

                st.markdown("---")
                st.write(f"🏷 **مجموع الأصناف:** {subtotal:.2f} د.أ")
                st.write(f"🛵 **التوصيل:** {delivery:.2f} د.أ")
                render_delivery_details(delivery_lines, delivery_uncertain)
                st.write(f"⚙️ **الخدمة:** {service:.2f} د.أ")
                st.markdown(f"### 💰 الإجمالي النهائي: {total:.2f} د.أ")
                render_min_order_notice(subtotal)

                if st.button("🗑 تفريغ السلة", use_container_width=True):
                    st.session_state.cart = []
                    st.rerun()

                payment = st.radio(
                    "اختر طريقة الدفع:",
                    ["نقداً عند الاستلام", "CliQ (0797088219)", "Zain Cash"],
                    key="pay_store_mode"
                )

                st.markdown("---")
                summary = "\n".join(f"- {item['name']} ({item['price']:.2f} د.أ) [المتجر: {item['merchant']}]" for item in st.session_state.cart)
                summary += delivery_summary_line(delivery, delivery_lines)
                
                if st.button("📌 تأكيد وإرسال للنظام", key="submit_store_mode", use_container_width=True) and order_ready(subtotal):
                    try:
                        sb.table("orders").insert({
                            "customer_name": st.session_state.customer_name,
                            "customer_phone": st.session_state.phone,
                            "customer_address": f"{st.session_state.customer_address} (ملاحظات: {st.session_state.delivery_notes}) | رابط الخريطة: {st.session_state.customer_map_link}",
                            "order_details": summary,
                            "total_amount": total,
                            "payment_method": payment,
                            "order_status": "قيد التجهيز",
                            "driver_name": "",
                            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }).execute()
                        notify_admin_new_order(summary, total, payment)

                        st.success("🎉 تم تأكيد طلبك بنجاح وإرساله للنظام!")
                        st.session_state.cart = []
                        st.rerun()
                    except Exception as e:
                        st.error(f"خطأ أثناء إرسال الطلب: {e}")

                render_whatsapp_option(summary, subtotal, delivery, service, total, payment, key_suffix="store")

            st.markdown('</div>', unsafe_allow_html=True)

    else:
        user_input = st.text_input(
            "🔍 ابحث عن متجر أو صنف (اكتب الحروف الأولى)...",
            value=st.session_state.search_query,
            key=f"user_search_box_{st.session_state.search_input_key}"
        )
        
        if user_input != st.session_state.search_query:
            st.session_state.search_query = user_input

        render_promos()

        st.markdown('<div class="kg-section-title">📁 الأقسام الرئيسية</div>', unsafe_allow_html=True)
        
        cols_per_row = 4
        for i in range(0, len(categories), cols_per_row):
            row_cats = categories[i:i + cols_per_row]
            c_cols = st.columns(len(row_cats))
            for j, cat in enumerate(row_cats):
                c_name = cat["name"]
                c_img = cat["image"]
                is_sel = (st.session_state.selected_category == c_name)
                ring = "3px solid #7B1FD6" if is_sel else "3px solid #F1ECF8"
                label_color = "#6A12C4" if is_sel else "#2D3142"
                bg_color = "#F3EAFD" if is_sel else "#F7F3EE"
                shadow_style = "box-shadow: 0 4px 14px rgba(123,31,214,0.25);" if is_sel else "box-shadow: 0 2px 8px rgba(0,0,0,0.05);"
                
                with c_cols[j]:
                    st.markdown(
                        f"""
                        <div class="kg-cat-card" style="background: {bg_color}; border-radius: 20px; padding: 14px 6px 10px 6px; text-align: center; margin-bottom: 8px; {shadow_style} height: 125px; display: flex; flex-direction: column; justify-content: center; align-items: center;">
                            <img src="{c_img}" style="width: 62px; height: 62px; object-fit: cover; border-radius: 50%; margin-bottom: 8px; border: {ring};">
                            <div class="kg-cat-name" style="font-weight: 800; font-size: 12px; color: {label_color}; width: 100%; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; padding: 0 2px;">{c_name}</div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                    btn_label = "✓" if is_sel else "عرض"
                    if st.button(btn_label, key=f"cat_card_{i+j}", use_container_width=True):
                        st.session_state.selected_category = c_name
                        st.query_params["cat"] = c_name
                        st.session_state.search_query = ""
                        st.session_state.search_input_key += 1
                        st.rerun()

        left, right = st.columns([2.2, 1], gap="large")

        with left:
            st.markdown('<div class="kg-section-title">🏬 المتاجر المعتمدة (اضغط على أي متجر لاستعراض أصنافه)</div>', unsafe_allow_html=True)

            if st.session_state.selected_category == "الكل":
                filtered_merchants = all_merchants
            else:
                selected_cat = st.session_state.selected_category.strip()
                filtered_merchants = [
                    m for m in all_merchants 
                    if str(m.get("category", "")).strip() == selected_cat
                ]

            current_search = st.session_state.search_query.strip()
            if current_search:
                s = current_search.lower()
                matching_merchants_by_product = set()
                for p in all_products:
                    if s in str(p.get("item_name") or "").lower():
                        matching_merchants_by_product.add(p.get("merchant_name"))

                merchants = []
                for m in filtered_merchants:
                    mname = str(m.get("name") or "").lower()
                    mcat = str(m.get("category") or "").lower()
                    if s in mname or s in mcat or m.get("name") in matching_merchants_by_product:
                        merchants.append(m)
            else:
                merchants = filtered_merchants

            if not merchants:
                st.info("لا توجد متاجر مطابقة للبحث أو مضافة حالياً في هذا القسم.")

            store_cols_count = 2
            for mi in range(0, len(merchants), store_cols_count):
                row_stores = merchants[mi:mi + store_cols_count]
                s_cols = st.columns(len(row_stores))
                for sj, store in enumerate(row_stores):
                    sname = store.get("name", "متجر")
                    scat = store.get("category", "")
                    sloc = store.get("location", "")
                    
                    with s_cols[sj]:
                        st.markdown('<div class="kg-store-card">', unsafe_allow_html=True)
                        img_col, info_col = st.columns([1, 1.6])
                        with img_col:
                            display_image(store.get("image_data"), width=90, fallback="🏬")
                        with info_col:
                            st.markdown(
                                f"""
                                <div class="kg-store-name">{sname}</div>
                                <span class="kg-chip"><span>{scat}</span></span>
                                <span class="kg-chip"><span>📍 {sloc}</span></span>
                                <span class="kg-chip kg-chip-green"><span>{fee_label(store)}</span></span>
                                """,
                                unsafe_allow_html=True
                            )
                        
                        if st.button(f"🛒 تصفح أصناف {sname}", key=f"enter_store_{mi+sj}", use_container_width=True):
                            st.session_state.selected_merchant = sname
                            st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)

        with right:
            st.markdown('<div class="kg-cart">', unsafe_allow_html=True)
            st.subheader("🛍 سلة الطلبات والفاتورة")

            if not st.session_state.cart:
                st.info("السلة فارغة حالياً.")
            else:
                subtotal = sum(safe_price(item.get("price")) for item in st.session_state.cart)

                for item in st.session_state.cart:
                    st.write(f"🔹 **{item['name']}**")
                    st.caption(f"{item['merchant']} | {item['price']:.2f} د.أ")

                delivery, delivery_lines, delivery_uncertain = compute_delivery(st.session_state.cart, all_merchants)
                service = 0.25
                total = subtotal + delivery + service

                st.markdown("---")
                st.write(f"🏷 **مجموع الأصناف:** {subtotal:.2f} د.أ")
                st.write(f"🛵 **التوصيل:** {delivery:.2f} د.أ")
                render_delivery_details(delivery_lines, delivery_uncertain)
                st.write(f"⚙️ **الخدمة:** {service:.2f} د.أ")
                st.markdown(f"### 💰 الإجمالي النهائي: {total:.2f} د.أ")
                render_min_order_notice(subtotal)

                if st.button("🗑 تفريغ السلة", key="clear_cart_main", use_container_width=True):
                    st.session_state.cart = []
                    st.rerun()

                payment = st.radio(
                    "اختر طريقة الدفع:",
                    ["نقداً عند الاستلام", "CliQ (0797088219)", "Zain Cash"],
                    key="pay_main_mode"
                )

                st.markdown("---")
                summary = "\n".join(f"- {item['name']} ({item['price']:.2f} د.أ) [المتجر: {item['merchant']}]" for item in st.session_state.cart)
                summary += delivery_summary_line(delivery, delivery_lines)
                
                if st.button("📌 تأكيد وإرسال للنظام", key="submit_main_mode", use_container_width=True) and order_ready(subtotal):
                    try:
                        sb.table("orders").insert({
                            "customer_name": st.session_state.customer_name,
                            "customer_phone": st.session_state.phone,
                            "customer_address": f"{st.session_state.customer_address} (ملاحظات: {st.session_state.delivery_notes}) | رابط الخريطة: {st.session_state.customer_map_link}",
                            "order_details": summary,
                            "total_amount": total,
                            "payment_method": payment,
                            "order_status": "قيد التجهيز",
                            "driver_name": "",
                            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }).execute()
                        notify_admin_new_order(summary, total, payment)

                        st.success("🎉 تم تأكيد طلبك بنجاح وإرساله للنظام!")
                        st.session_state.cart = []
                        st.rerun()
                    except Exception as e:
                        st.error(f"خطأ أثناء إرسال الطلب: {e}")

                render_whatsapp_option(summary, subtotal, delivery, service, total, payment, key_suffix="main")

            st.markdown('</div>', unsafe_allow_html=True)


# ============================================================
# 2. الطلبات وتتبع الرحلة
# ============================================================
elif st.session_state.nav_tab == "الطلبات":
    render_top_header(
        "📦 طلباتي ومتابعة رحلة التوصيل",
        "تابع حالة طلبك خطوة بخطوة من التجهيز وحتى الوصول",
        show_deliver=False
    )

    try:
        phone_now = (st.session_state.phone or "").strip()
        orders = (sb.table("orders").select("*").eq("customer_phone", phone_now).order("id", desc=True).execute().data or []) if phone_now else []
        if orders:
            for ord_item in orders:
                status = ord_item.get('order_status', 'قيد التجهيز')
                driver = ord_item.get('driver_name', '')
                
                steps = ["قيد التجهيز", "استلم السائق الطلب", "في الطريق", "تم الاستلام"]
                current_step_idx = 0
                if status in steps:
                    current_step_idx = steps.index(status)
                elif status == "جاهز":
                    current_step_idx = 1
                
                st.markdown(f"""
                <div style="background:white; border-radius:20px; padding:20px; margin-bottom:15px; border:1px solid #E5DDF3; box-shadow: 0 4px 15px rgba(106,18,196,0.06);">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                        <span style="font-size:16px; font-weight:900; color:#6A12C4;">رقم الطلب: #{ord_item.get('id')}</span>
                        <span style="background:#D7FF3B; color:#1B1B1B; padding:4px 12px; border-radius:20px; font-weight:bold; font-size:12px;">الحالة: {status}</span>
                    </div>
                    <p style="margin:5px 0; font-size:13px; color:#64748B;"><b>وقت الطلب:</b> {ord_item.get('created_at')}</p>
                    <p style="margin:5px 0; font-size:13px; color:#64748B;"><b>المبلغ الإجمالي:</b> {ord_item.get('total_amount')} د.أ</p>
                    <hr style="margin:10px 0; border:0; border-top:1px solid #F1ECF8;">
                """, unsafe_allow_html=True)
                
                st.markdown("📍 **رحلة الطلب المباشرة:**")
                prog_cols = st.columns(4)
                for s_idx, s_name in enumerate(steps):
                    with prog_cols[s_idx]:
                        if s_idx <= current_step_idx:
                            st.markdown(f"<div style='background:#7B1FD6; color:white; padding:6px; border-radius:20px; text-align:center; font-size:11px; font-weight:bold;'>✓ {s_name}</div>", unsafe_allow_html=True)
                        else:
                            st.markdown(f"<div style='background:#F1ECF8; color:#94A3B8; padding:6px; border-radius:20px; text-align:center; font-size:11px;'>{s_name}</div>", unsafe_allow_html=True)
                
                if current_step_idx >= 1:
                    st.markdown("<br>", unsafe_allow_html=True)
                    col_d1, col_d2 = st.columns(2)
                    with col_d1:
                        driver_display = driver if driver else "جارٍ تعيين سائق..."
                        st.markdown(f"🛵 **السائق المسؤول:** `{driver_display}`")
                    with col_d2:
                        st.markdown("⏱ **الوقت المتوقع للوصول:** `خلال 15-20 دقيقة`")

                if st.session_state.customer_map_link:
                    st.markdown(f'<div style="margin-top:10px;"><a href="{st.session_state.customer_map_link}" target="_blank" style="background:#6A12C4; color:white; padding:8px 16px; border-radius:20px; font-size:12px; text-decoration:none; display:inline-block;">🗺 عرض موقع تسليم الطلب على خرائط جوجل (مسار الرحلة)</a></div>', unsafe_allow_html=True)

                with st.expander("📄 تفاصيل الأصناف المطلوبة"):
                    st.code(ord_item.get('order_details', ''), language=None)

                st.markdown("</div>", unsafe_allow_html=True)
        else:
            info_col1, info_col2 = st.columns([4, 1])
            with info_col1:
                st.info("لا توجد طلبات سابقة مسجلة برقم هاتفك الحالي." if phone_now else "أدخل رقم هاتفك من صفحة «حسابي» لعرض طلباتك.")
            with info_col2:
                if st.button("🔄 تحديث الطلبات", use_container_width=True):
                    st.rerun()
    except Exception as e:
        st.error(f"تعذر جلب الطلبات: {e}")


# ============================================================
# 3. الحساب وعنوان التوصيل مع ربط الخريطة الفعّال
# ============================================================
elif st.session_state.nav_tab == "الحساب":
    render_top_header(
        "👤 حسابي وعنوان التوصيل",
        "قم بتحديث معلوماتك، تحديد موقعك الجغرافي برابط خرائط جوجل، أو إدارة حسابك بكل سهولة",
        show_deliver=False
    )

    st.session_state.customer_name = st.text_input("اسمك الكريم:", value=st.session_state.customer_name)
    
    old_phone_val = st.session_state.phone
    st.session_state.phone = st.text_input("رقم الهاتف (المعرف الأساسي):", value=st.session_state.phone)
    
    st.session_state.customer_email = st.text_input("البريد الإلكتروني (اختياري):", value=st.session_state.customer_email)
    st.session_state.customer_address = st.text_area("تفاصيل العنوان أو المنطقة (المدينة، الحي، الشارع):", value=st.session_state.customer_address)
    st.session_state.delivery_notes = st.text_area("ملاحظات خاصة لمندوب التوصيل:", value=st.session_state.delivery_notes)

    st.markdown("📍 **الموقع الجغرافي (ربط رابط خرائط جوجل الفعّال):**")
    st.markdown("<p style='font-size:12px; color:#64748B; margin-top:-5px;'>يُرجى إدخال رابط فعال من خرائط جوجل لموقعك بدقة لضمان وصول السائق للمنطقة فوراً.</p>", unsafe_allow_html=True)

    st.session_state.customer_map_link = normalize_map_link(
        st.text_input("رابط موقعك على خرائط جوجل (Google Maps URL):", value=st.session_state.customer_map_link)
    )

    map_cols = st.columns(2)
    with map_cols[0]:
        st.markdown(
            '<a href="https://www.google.com/maps" target="_blank" rel="noopener noreferrer" style="display:block; text-align:center; background:#FF5A00; color:#FFFFFF !important; font-weight:bold; font-size:13px; padding:9px 12px; border-radius:24px; text-decoration:none;">🌐 فتح خرائط جوجل لنسخ الرابط</a>',
            unsafe_allow_html=True
        )
        st.caption("💡 يُفتح في تبويب جديد: ابحث عن موقعك، اضغط «مشاركة» (Share)، انسخ الرابط، ثم ارجع والصقه في الحقل أعلاه.")
    with map_cols[1]:
        if st.button("🧹 مسح رابط الموقع الحالي"):
            st.session_state.customer_map_link = ""
            st.success("✅ تم مسح رابط الموقع. الصق رابط موقعك الجديد في الحقل أعلاه.")
            st.rerun()

    # معاينة الرابط الفعّال إذا كان موجوداً
    if st.session_state.customer_map_link:
        st.markdown(f'<div style="margin:10px 0; padding:10px; background:#F3EAFD; border:1px solid #7B1FD6; border-radius:12px;"><a href="{st.session_state.customer_map_link}" target="_blank" style="color:#6A12C4; font-weight:bold; text-decoration:none;">🗺 انقر هنا لمعاينة موقعك المسجل على خريطة جوجل (تأكيد فعالية الرابط)</a></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # أزرار الإجراءات المستقلة
    col_b1, col_b2, col_b3 = st.columns(3)

    with col_b1:
        if st.button("💾 حفظ وتحديث البيانات", use_container_width=True):
            try:
                sb.table("customers").upsert(
                    {
                        "name": st.session_state.customer_name,
                        "phone": st.session_state.phone,
                        "address": f"{st.session_state.customer_address} (ملاحظات: {st.session_state.delivery_notes}) | البريد: {st.session_state.customer_email} | رابط الخريطة: {st.session_state.customer_map_link}"
                    },
                    on_conflict="phone"
                ).execute()
                st.success("🎉 تم حفظ وتحديث بياناتك ورابط الموقع بنجاح!")
            except Exception as e:
                st.error(f"خطأ أثناء الحفظ: {e}")

    with col_b2:
        if st.button("🔄 تغيير الرقم / الانتقال لمنطقة أخرى", use_container_width=True):
            try:
                if old_phone_val != st.session_state.phone:
                    sb.table("customers").delete().eq("phone", old_phone_val).execute()

                sb.table("customers").upsert(
                    {
                        "name": st.session_state.customer_name,
                        "phone": st.session_state.phone,
                        "address": f"{st.session_state.customer_address} (ملاحظات: {st.session_state.delivery_notes}) | البريد: {st.session_state.customer_email} | رابط الخريطة: {st.session_state.customer_map_link}"
                    },
                    on_conflict="phone"
                ).execute()
                st.success("🎉 تم اعتماد الرقم الجديد والمنطقة ورابط الخريطة بنجاح!")
            except Exception as e:
                st.error(f"خطأ أثناء تحديث رقم الهاتف أو المنطقة: {e}")

    with col_b3:
        if st.button("🗑 مسح وحذف الحساب", use_container_width=True):
            try:
                sb.table("customers").delete().eq("phone", st.session_state.phone).execute()
                st.session_state.customer_name = ""
                st.session_state.customer_address = ""
                st.session_state.delivery_notes = ""
                st.session_state.customer_email = ""
                st.session_state.customer_map_link = ""
                st.success("🗑 تم مسح وحذف بيانات الحساب من النظام بنجاح.")
                st.rerun()
            except Exception as e:
                st.error(f"خطأ أثناء حذف الحساب: {e}")
