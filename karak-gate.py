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
# مكتبة تحديد الموقع الجغرافي
# ============================================================
try:
    from streamlit_js_eval import get_geolocation
    HAS_GEOLOCATION = True
except Exception:
    HAS_GEOLOCATION = False


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
ROAD_FACTOR = 1.3             # معامل تقريبي لتحويل المسافة المباشرة إلى مسافة طريق
MIN_ORDER_SUBTOTAL = 5.00     # الحد الأدنى لقيمة الطلب (بدون التوصيل والخدمة)


# ============================================================
# إعدادات العروض التسويقية
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

/* ---------- بطاقة القسم ---------- */
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

/* ---------- الأقسام على الهاتف ---------- */
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

if "customer_lat" not in st.session_state:
    st.session_state.customer_lat = None

if "customer_lng" not in st.session_state:
    st.session_state.customer_lng = None

if "do_geolocate" not in st.session_state:
    st.session_state.do_geolocate = False

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


def safe_price(value):
    try:
        return float(value or 0)
    except Exception:
        return 0.0


# ============================================================
# دالة رسم الهيدر
# ============================================================
def flat_html(html):
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
# أجور التوصيل
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

    # أولوية: إحداثيات المتصفح المحفوظة، ثم الرابط اليدوي
    cust = None
    if st.session_state.get("customer_lat") and st.session_state.get("customer_lng"):
        cust = (st.session_state.customer_lat, st.session_state.customer_lng)
    elif st.session_state.customer_map_link:
        cust = extract_coords(st.session_state.customer_map_link)

    total = 0.0
    lines = []
    uncertain = False
    for name in dict.fromkeys(item.get("merchant") for item in cart):
        m = by_name.get(name) or {}
        base, per_km = merchant_fee_info(m)
        fee = base
        dist = None
        if per_km > 0:
            store_xy = merchant_coords(m)
            if cust and store_xy:
                dist = haversine_km(cust, store_xy) * ROAD_FACTOR
                fee = base + per_km * dist
                fee = math.ceil(fee * 4) / 4
            else:
                uncertain = True
        total += fee
        lines.append((name, fee, dist))
    return total, lines, uncertain


def render_delivery_details(lines, uncertain):
    for name, fee, dist in lines:
        extra = f" ({dist:.1f} كم تقريباً)" if dist is not None else ""
        st.caption(f"🛵 {name}: {fee:.2f} د.أ{extra}")
    if uncertain:
        st.caption("⚠️ تعذّر حساب المسافة (رابط موقعك أو موقع المتجر غير محدد)، فقد تؤكد الإدارة أجرة التوصيل النهائية.")


# ============================================================
# دوال واتساب
# ============================================================
def build_whatsapp_link(summary, subtotal, delivery, service, total, payment):
    addr = (st.session_state.customer_address or "").strip() or "غير محدد"
    notes = (st.session_state.delivery_notes or "").strip() or "-"
    map_link = (st.session_state.customer_map_link or "").strip() or "-"
    geo_str = "-"
    if st.session_state.get("customer_lat") and st.session_state.get("customer_lng"):
        geo_str = f"{st.session_state.customer_lat},{st.session_state.customer_lng}"
    msg = (
        "طلب جديد من تطبيق بوابة الكرك\n"
        f"الاسم: {st.session_state.customer_name}\n"
        f"الهاتف: {st.session_state.phone}\n"
        f"العنوان: {addr}\n"
        f"ملاحظات: {notes}\n"
        f"رابط الموقع: {map_link}\n"
        f"إحداثيات GPS: {geo_str}\n"
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


def order_ready():
    miss = missing_fields()
    if miss:
        st.error("⚠️ يرجى إكمال بياناتك من صفحة «حسابي» قبل إرسال الطلب: " + "، ".join(miss))
        return False
    return True


def check_min_order(cart):
    """يتحقق أن مجموع الأصناف يحقق الحد الأدنى"""
    subtotal = sum(safe_price(item.get("price")) for item in cart)
    return subtotal >= MIN_ORDER_SUBTOTAL, subtotal


def insert_order(summary, total, payment):
    geo_str = ""
    if st.session_state.get("customer_lat") and st.session_state.get("customer_lng"):
        geo_str = f" | إحداثيات: {st.session_state.customer_lat},{st.session_state.customer_lng}"

    sb.table("orders").insert({
        "customer_name": st.session_state.customer_name,
        "customer_phone": st.session_state.phone,
        "customer_address": f"{st.session_state.customer_address} (ملاحظات: {st.session_state.delivery_notes}) | رابط الخريطة: {st.session_state.customer_map_link}{geo_str}",
        "order_details": summary,
        "total_amount": total,
        "payment_method": payment,
        "order_status": "قيد التجهيز",
        "driver_name": "",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }).execute()


def render_whatsapp_option(summary, subtotal, delivery, service, total, payment, key_suffix="main", min_ok=True):
    miss = missing_fields()
    if miss:
        st.warning("⚠️ أكمل بياناتك من صفحة «حسابي» قبل الإرسال: " + "، ".join(miss))
    if not min_ok:
        st.warning(f"⚠️ لا يمكن الإرسال: الحد الأدنى لقيمة الطلب هو {MIN_ORDER_SUBTOTAL:.2f} د.أ قبل التوصيل والخدمة.")
    st.markdown(
        "<div style='text-align:center; font-size:12px; color:#64748B; margin:6px 0;'>— أو —</div>",
        unsafe_allow_html=True
    )
    if st.button(
        "📲 تسجيل الطلب وإرساله عبر واتساب",
        key=f"submit_wa_{key_suffix}",
        use_container_width=True,
        disabled=(not min_ok or bool(miss))
    ):
        if not order_ready():
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
                st.markdown(f'<a href="{m_data.get("map_link")}" target="_blank" style="color:#6A12C4; font-weight:bold; text-decoration:none; display:inline-block; margin-bottom:15px;">🗺 فتح موقع المتجر على
