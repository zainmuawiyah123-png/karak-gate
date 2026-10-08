import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sys
import io
import base64
import html
from datetime import datetime
import streamlit as st
from supabase import create_client

APP_NAME = "Halago"

try:
    from driver_map import coords_from_map_link, merchant_coords, route_info
    GEO_OK = True
except Exception:
    GEO_OK = False

try:
    from push_service import send_push
    PUSH_IMPORT_OK = True
except Exception:
    PUSH_IMPORT_OK = False

def push_ready():
    try:
        return bool(st.secrets.get("SUPABASE_SERVICE_KEY")) and bool(st.secrets.get("VAPID_PRIVATE_KEY"))
    except Exception:
        return False
import sys
import io
import re
import time
import base64
import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime

import streamlit as st
from supabase import create_client

# ---- أدوات الحزمة: إن لم تُرفع الملفات يعمل التطبيق بدونها ----
try:
    from driver_map import coords_from_map_link, merchant_coords, route_info
    GEO_OK = True
except Exception:
    GEO_OK = False

try:
    from fees import DEFAULT_PER_KM, DEFAULT_BASE_FEE
except Exception:
    DEFAULT_PER_KM, DEFAULT_BASE_FEE = 0.25, 1.50

try:
    from push_service import send_push
    PUSH_IMPORT_OK = True
except Exception:
    PUSH_IMPORT_OK = False

from auth_pin import (valid_pin, valid_phone, norm_phone, set_pin, find_by_phone, check_pin, NO_PIN)


def push_ready():
    try:
        return bool(st.secrets.get("SUPABASE_SERVICE_KEY")) and bool(st.secrets.get("VAPID_PRIVATE_KEY"))
    except Exception:
        return False


def _setting_value(name):
    """قراءة الإعداد من Render أولاً ثم من Streamlit Secrets."""
    value = os.environ.get(name, "").strip()
    if value:
        return value
    try:
        return str(st.secrets.get(name, "") or "").strip()
    except Exception:
        return ""


def telegram_send(text):
    """إرسال إشعار تيليجرام وإرجاع (نجح، رسالة تشخيصية)."""
    token = _setting_value("TELEGRAM_BOT_TOKEN")
    chat_id = _setting_value("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return False, "لم يتم ضبط TELEGRAM_BOT_TOKEN أو TELEGRAM_CHAT_ID في Render."
    try:
        payload = json.dumps({"chat_id": chat_id, "text": text}).encode("utf-8")
        request = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            result = json.loads(response.read().decode("utf-8"))
        if result.get("ok"):
            return True, "تم إرسال إشعار تيليجرام."
        return False, str(result.get("description") or "رفض Telegram الطلب.")
    except urllib.error.HTTPError as exc:
        try:
            body = json.loads(exc.read().decode("utf-8"))
            return False, str(body.get("description") or f"Telegram HTTP {exc.code}")
        except Exception:
            return False, f"Telegram HTTP {exc.code}"
    except Exception:
        # لا نمنع تسجيل الطلب إذا كان تيليجرام متوقفًا أو إعداداته ناقصة.
        return False, "تعذر الاتصال بواجهة Telegram API."


PUSH_ON = PUSH_IMPORT_OK and push_ready()

MIN_ORDER = 5.0
SERVICE_FEE = 0.25
WA_NUMBER = "962797088219"
PAGE_SIZE = 40

# ============================================================
# UTF-8 (محمي)
# ============================================================
try:
    if sys.stdout and hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    if sys.stderr and hasattr(sys.stderr, "buffer"):
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
except Exception:
    pass


# ============================================================
# إعداد الصفحة — أول أمر Streamlit في الملف (مصحّح)
# ============================================================
st.set_page_config(
    page_title="Halago",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="collapsed"
)


# ============================================================
# Supabase
# ============================================================
SUPABASE_URL = "https://tzkdxodvlzggmcntnqer.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InR6a2R4b2R2bHpnZ21jbnRucWVyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTA5MzM3MzksImV4cCI6MjEwNjUwOTczOX0.M944yHglTXVyPrxySSQj0MBaqpr2I_8ub7Uoofbd2_4"

try:
    if "SUPABASE_ANON_KEY" in st.secrets:
        SUPABASE_ANON_KEY = str(st.secrets["SUPABASE_ANON_KEY"]).strip()
except Exception:
    pass


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
/* إخفاء العلامات العائمة الخاصة بـ Streamlit/الاستضافة أسفل الشاشة */
[data-testid="stStatusWidget"],
[data-testid="stToolbar"],
[data-testid="stDecoration"],
.stAppDeployButton,
.viewerBadge_container__1QSob,
.viewerBadge_link__1S3i2,
div[class*="viewerBadge"],
div[class*="stStatusWidget"] {
    display: none !important;
    visibility: hidden !important;
    pointer-events: none !important;
}
.stApp {
    background: #FFFFFF !important;
    color: #2D3142 !important;
}
.block-container {
    padding-top: 0.55rem !important;
    padding-bottom: 4rem !important;
    max-width: 1400px !important;
}
h1, h2, h3, h4, h5, h6, p, label, span {
    color: #2D3142 !important;
}
div[data-testid="column"] .stButton > button {
    background: #FF5722 !important;
    color: #FFFFFF !important;
    border-radius: 8px !important;
    border: 0 !important;
    font-weight: bold !important;
    font-size: 13px !important;
    padding: 6px 12px !important;
    min-height: 36px !important;
    margin: 4px auto 0 auto !important;
    display: block !important;
    width: 100% !important;
}
.kg-header {
    background: linear-gradient(135deg, #F4510B 0%, #FF6B1A 100%);
    border-radius: 0 0 28px 28px;
    padding: 22px 20px 25px;
    margin: -10px -5px 18px;
    box-shadow: 0 8px 22px rgba(244,81,11,0.22);
}
.kg-header-title {
    color: white !important;
    font-size: 20px;
    font-weight: 800;
    margin: 0;
}
.kg-header-sub {
    color: white !important;
    font-size: 12px;
    margin: 0;
    opacity: 0.9;
}
.kg-store-card {
    background: white;
    border-radius: 16px;
    padding: 16px;
    margin-bottom: 15px;
    border: 1px solid #E2E8F0;
    box-shadow: 0 4px 15px rgba(0,0,0,0.03);
    text-align: center;
    transition: all 0.3s ease;
}
.kg-store-card:hover {
    border-color: #E64A19;
    box-shadow: 0 6px 20px rgba(230,74,25,0.15);
}
.kg-store-badge { display:inline-block; background:#FFF0E6; color:#D84315 !important; border-radius:20px; padding:4px 9px; font-size:10px; font-weight:800; margin:4px 0; }
.kg-store-meta { color:#64748B !important; font-size:11px; line-height:1.8; }
.kg-store-meta b { color:#374151 !important; }
.kg-cart {
    background: white;
    border-radius: 16px;
    padding: 18px;
    border: 1px solid #E2E8F0;
    box-shadow: 0 4px 20px rgba(0,0,0,0.04);
}
.kg-cart-progress { background:#FFF7EF; border:1px solid #F6E6D7; border-radius:10px; padding:8px 10px; color:#7A341E !important; font-size:12px; margin:8px 0; }

/* ============ إعلان علوي مشوّق ============ */
.kg-ad {
    background: linear-gradient(135deg, #0B3D91 0%, #1565C0 50%, #0B3D91 100%);
    border-radius: 14px;
    padding: 14px 18px;
    margin-bottom: 15px;
    text-align: center;
    color: #FFD700 !important;
    font-weight: 800;
    font-size: 15px;
    box-shadow: 0 4px 15px rgba(11,61,145,0.35);
    border: 2px solid #FFD700;
    animation: kgPulse 2.5s ease-in-out infinite;
}
.kg-ad span { color: #FFD700 !important; }
@keyframes kgPulse {
    0%, 100% { box-shadow: 0 4px 15px rgba(11,61,145,0.35); }
    50%      { box-shadow: 0 4px 25px rgba(255,215,0,0.55); }
}

/* ============ شريط التوصيل الأصفر ============ */
.kg-delivery-bar {
    background: linear-gradient(90deg, #FFD700 0%, #FFEB3B 100%);
    border: 2px solid #F9A825;
    border-radius: 12px;
    padding: 10px 14px;
    margin: 10px 0;
    color: #4A3800 !important;
    font-weight: 800;
    text-align: center;
    font-size: 14px;
}
.kg-delivery-bar span { color: #4A3800 !important; }

/* ============ نجوم التقييم ============ */
.kg-rating {
    color: #F9A825 !important;
    font-size: 14px;
    margin-top: 4px;
    font-weight: 700;
}
.kg-rating-stars { color:#F9A825 !important; letter-spacing:1px; }
.kg-rating-value { color:#64748B !important; font-size:11px; font-weight:500; }

@keyframes kgfade { from {opacity:0; transform:scale(.92);} to {opacity:1; transform:scale(1);} }
@keyframes kgspin { to { transform: rotate(360deg); } }

/* ============ تصغير بطاقة الأقسام ============ */
.kg-cat-card {
    background: #FFF7EF;
    border: 1px solid #F6E6D7;
    border-radius: 12px;
    padding: 3px 2px;
    text-align: center;
    margin: 0 auto 3px;
    height: 70px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
}
.kg-cat-card img {
    width: 44px !important;
    height: 44px !important;
    object-fit: cover;
    border-radius: 12px;
    margin-bottom: 4px;
    border: 1px solid #F1F5F9;
    background: #FFF7F0;
    box-shadow: 0 2px 7px rgba(0,0,0,.08);
}
.kg-cat-card .kg-cat-name {
    font-weight: 800;
    font-size: 11px;
    color: #2D3142 !important;
    width: 100%;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    padding: 0 2px;
}
.kg-cat-card.kg-sel {
    background: #FFF0E6;
    border-color: #FF8A5B;
    box-shadow: 0 3px 10px rgba(244,81,11,.14);
}
/* زر القسم يكون بعرض النص فقط وليس بعرض العمود كاملًا */
div[data-testid="column"]:has(.kg-cat-card) .stButton > button {
    width: auto !important;
    min-width: 0 !important;
    max-width: 100% !important;
    padding: 3px 8px !important;
    margin: 0 auto !important;
    display: block !important;
    font-size: 11px !important;
    min-height: 28px !important;
}
div[data-testid="column"]:has(.kg-cat-card) div[data-testid="stButton"] {
    width: fit-content !important;
    max-width: 100% !important;
    margin: 0 auto !important;
}
div[data-testid="column"]:has(.kg-cat-card) div[data-testid="stButton"] > div {
    width: fit-content !important;
    max-width: 100% !important;
    margin: 0 auto !important;
}
.kg-home-title { color:#FFFFFF !important; font-size:27px; font-weight:900; margin:0; }
.kg-home-sub { color:#FFF7F2 !important; font-size:13px; margin-top:5px; }
.kg-location { color:#FFFFFF !important; font-size:14px; margin-bottom:13px; }
.kg-location b { color:#FFFFFF !important; }
.kg-search-hint { background:#FFFFFF; color:#64748B !important; border-radius:28px; padding:13px 18px; font-size:15px; margin-top:13px; box-shadow:0 3px 10px rgba(0,0,0,.12); }
.kg-section-title { font-size:20px; font-weight:900; color:#202124 !important; margin:20px 0 10px; }
.kg-promo { background:#FFF0E5; border-radius:16px; padding:0; height:58px; margin:16px 0; border:1px solid #FFE0CC; overflow:hidden; display:flex; align-items:center; }
.kg-marquee { display:flex; width:max-content; white-space:nowrap; animation:kgMarquee 24s linear infinite; direction:ltr; }
.kg-marquee-item { display:inline-flex; align-items:center; gap:10px; margin-right:80px; color:#5B1710 !important; font-size:15px; font-weight:900; }
.kg-marquee-item b { background:#5B1710; color:#D9FF00 !important; border-radius:6px; padding:5px 10px; }
@keyframes kgMarquee { from { transform:translateX(0); } to { transform:translateX(-50%); } }
.kg-promo-title { color:#5B1710 !important; font-size:22px; font-weight:900; line-height:1.25; max-width:58%; }
.kg-promo-sub { color:#7A2A1C !important; font-size:13px; margin-top:8px; max-width:58%; }
.kg-promo-badge { display:inline-block; background:#5B1710; color:#D9FF00 !important; padding:7px 12px; margin-top:13px; font-size:18px; font-weight:900; transform:rotate(-3deg); }
.kg-cat-card img { background:#FFF7F0; }
@media (max-width: 640px) {
    .block-container { padding-left: .75rem !important; padding-right: .75rem !important; }
    .kg-header { margin-left:-12px; margin-right:-12px; }
    .kg-cat-card { height:67px; padding:1px; border-radius:10px; margin-bottom:2px; }
    .kg-cat-card img { width:44px !important; height:44px !important; margin-bottom:1px; }
    .kg-cat-card .kg-cat-name { font-size:11px; }
    .kg-promo { height:52px; border-radius:13px; }
    .kg-marquee-item { font-size:13px; margin-right:55px; }
}
</style>
""",
    unsafe_allow_html=True
)


# ============================================================
# شاشة الترحيب
# ============================================================
if not st.session_state.get("splash_done"):
    _splash = st.empty()
    _splash.markdown(
        """
        <div style="position:fixed; inset:0; z-index:999999; display:flex; flex-direction:column;
                    align-items:center; justify-content:center; text-align:center;
                    background:linear-gradient(135deg,#0B3D91 0%,#1565C0 100%);">
            <div style="font-size:84px; animation:kgfade .8s ease both;">🛒</div>
            <div style="font-size:44px; font-weight:900; color:#FFD700 !important; animation:kgfade 1s ease both; letter-spacing:1px;">Halago</div>
            <div style="font-size:15px; color:#FFFFFF !important; opacity:.9; margin-top:6px;">هلا بك... اطلب براحة</div>
            <div style="font-size:15px; color:#FFD700 !important; opacity:.95; margin-top:14px;">اطلب ما تريد من متاجر الكرك بكل سهولة</div>
            <div style="margin-top:28px; width:34px; height:34px; border:4px solid rgba(255,215,0,.35);
                        border-top-color:#FFD700; border-radius:50%; animation:kgspin 1s linear infinite;"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    time.sleep(3)
    _splash.empty()
    st.session_state["splash_done"] = True


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
# تحميل البيانات
# ============================================================
@st.cache_data(ttl=30, show_spinner=False)
def load_merchants():
    try:
        return sb.table("merchants").select("*").eq("status", "معتمد").execute().data or []
    except Exception:
        return []


@st.cache_data(ttl=30, show_spinner=False)
def merchants_with_product(q):
    try:
        rows = sb.table("products").select("merchant_name").ilike("item_name", f"%{q}%").limit(1000).execute().data or []
        return {r.get("merchant_name") for r in rows}
    except Exception:
        return set()


@st.cache_data(ttl=30, show_spinner=False)
def load_products(merchant, q, page):
    try:
        qr = (sb.table("products")
              .select("id,item_name,price,quantity,unit,image_path", count="exact")
              .eq("merchant_name", merchant))
        if q:
            qr = qr.ilike("item_name", f"%{q}%")
        res = qr.order("id").range(page * PAGE_SIZE, page * PAGE_SIZE + PAGE_SIZE - 1).execute()
        return res.data or [], (res.count if res.count is not None else len(res.data or []))
    except Exception:
        return [], 0


def maybe_autorefresh():
    try:
        from streamlit_autorefresh import st_autorefresh
        st_autorefresh(interval=8000, key="customer_auto_refresh")
    except Exception:
        pass


# ============================================================
# Session State
# ============================================================
for _k, _v in {
    "logged_in": False, "customer_id": None,
    "phone": "", "customer_name": "", "customer_email": "",
    "customer_address": "", "delivery_notes": "", "customer_map_link": "",
    "cart": [], "nav_tab": "الرئيسية", "search_query": "", "search_input_key": 0,
    "selected_merchant": None, "store_q": "", "store_page": 0, "last_order": None,
}.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

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


def coords_from_customer_link(link):
    """استخراج latitude/longitude من روابط Google Maps العادية والمختصرة."""
    raw = str(link or "").strip()
    if not raw:
        return None

    candidates = [raw]
    if raw.startswith(("http://", "https://")) and ("maps.app.goo.gl" in raw or "goo.gl/maps" in raw):
        try:
            req = urllib.request.Request(raw, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=6) as response:
                candidates.append(response.geturl())
        except Exception:
            pass

    for candidate in candidates:
        text = urllib.parse.unquote(str(candidate)).replace("%2C", ",")
        patterns = (
            r"[?&](?:q|query|ll|center)=(-?\d{1,3}(?:\.\d+)?)[, ](-?\d{1,3}(?:\.\d+)?)",
            r"@(-?\d{1,3}(?:\.\d+)?),(-?\d{1,3}(?:\.\d+)?)",
            r"!3d(-?\d{1,3}(?:\.\d+)?)!4d(-?\d{1,3}(?:\.\d+)?)",
        )
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                lat, lng = float(match.group(1)), float(match.group(2))
                if -90 <= lat <= 90 and -180 <= lng <= 180:
                    return lat, lng
    return None


def customer_map_coords(link):
    """استخدم driver_map إن توفر، وإلا استخدم المحلل الداخلي."""
    if not link:
        return None
    if GEO_OK:
        try:
            result = coords_from_map_link(link)
            if result:
                return result
        except Exception:
            pass
    return coords_from_customer_link(link)


def merchant_badge(merchant):
    """شارة تسويقية من بيانات المتجر إن وُجدت، وإلا شارة آمنة افتراضية."""
    for key in ("badge", "label", "tag"):
        value = str(merchant.get(key) or "").strip()
        if value:
            return value
    return "متجر معتمد"


def merchant_eta(merchant):
    """وقت تقديري قابل للتخصيص من بيانات المتجر دون إنشاء أعمدة جديدة."""
    for key in ("delivery_time", "estimated_time", "eta"):
        value = str(merchant.get(key) or "").strip()
        if value:
            return value
    return "25–40 دقيقة"


# ============================================================
# عرض الصور
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
# التقييم اليدوي (نجوم من حقل rating في جدول merchants)
# ============================================================
def render_rating(merchant):
    """يعرض نجوم التقييم أسفل المتجر، مع دعم أسماء الحقول الشائعة."""
    try:
        raw_rating = (
            merchant.get("rating")
            if merchant.get("rating") is not None
            else merchant.get("avg_rating", merchant.get("average_rating", 0))
        )
        rating = max(0.0, min(5.0, float(raw_rating or 0)))
    except Exception:
        rating = 0.0
    full = int(rating)
    half = 1 if (rating - full) >= 0.5 else 0
    empty = 5 - full - half
    stars = "★" * full + ("⯨" if half else "") + "☆" * empty
    label = f"({rating:.1f})" if rating > 0 else "(لا يوجد تقييم بعد)"
    st.markdown(
        f"<div class='kg-rating'><span class='kg-rating-stars'>{stars}</span> <span class='kg-rating-value'>{label}</span></div>",
        unsafe_allow_html=True
    )


# ============================================================
# الحساب: PIN
# ============================================================
def legacy_split(address):
    addr, notes, link = str(address or ""), "", ""
    m = re.search(r"\|\s*رابط الخريطة:\s*(\S+)", addr)
    if m:
        link = m.group(1)
    addr = re.sub(r"\|\s*البريد:.*?(?=\||$)", "", addr)
    addr = re.sub(r"\|\s*رابط الخريطة:\s*\S+", "", addr)
    m = re.search(r"\(ملاحظات:\s*(.*?)\)", addr)
    if m:
        notes = m.group(1)
        addr = addr.replace(m.group(0), "")
    return addr.strip(" |"), notes.strip(), link


def login_session(row):
    addr, notes, link = row.get("address") or "", row.get("delivery_notes") or "", row.get("map_link") or ""
    if "رابط الخريطة:" in addr or "(ملاحظات:" in addr:
        l_addr, l_notes, l_link = legacy_split(addr)
        addr, notes, link = l_addr, notes or l_notes, link or l_link
    st.session_state.update({
        "logged_in": True, "customer_id": row.get("id"), "phone": row.get("phone") or "",
        "customer_name": row.get("name") or "", "customer_address": addr,
        "delivery_notes": notes, "customer_map_link": link, "customer_email": row.get("email") or "",
    })


def customer_payload(phone):
    xy = None
    if st.session_state.customer_map_link:
        xy = customer_map_coords(st.session_state.customer_map_link)
    p = {
        "name": st.session_state.customer_name, "phone": phone,
        "address": st.session_state.customer_address, "delivery_notes": st.session_state.delivery_notes,
        "map_link": st.session_state.customer_map_link, "email": st.session_state.customer_email,
    }
    if xy:
        p["lat"], p["lng"] = xy
    return p


def render_auth():
    st.markdown(
        """
        <div class="kg-header">
            <div class="kg-header-title">🛒 Halago</div>
            <div class="kg-header-sub">سجّل دخولك أو أنشئ حسابًا جديدًا لتبدأ الطلب</div>
        </div>
        """,
        unsafe_allow_html=True
    )
    mode = st.radio("اختر:", ["تسجيل دخول", "حساب جديد"], horizontal=True, key="auth_mode")

    if mode == "تسجيل دخول":
        with st.form("login_form"):
            phone = st.text_input("رقم الهاتف (مثال: 0797123456)")
            pin = st.text_input("رمز PIN (4 أرقام)", type="password", max_chars=4)
            go = st.form_submit_button("دخول", use_container_width=True)
        if go:
            if not valid_phone(phone) or not valid_pin(pin):
                st.error("أدخل رقم هاتف أردني صحيح ورمز PIN من 4 أرقام.")
            else:
                row = find_by_phone(sb, "customers", phone)
                if not row:
                    st.error("لا يوجد حساب بهذا الرقم. اختر «حساب جديد».")
                else:
                    ok, msg = check_pin(sb, "customers", row, pin)
                    if ok:
                        login_session(row)
                        st.rerun()
                    elif msg == NO_PIN:
                        st.warning("حسابك قديم بلا رمز PIN. اختر «حساب جديد» بنفس الرقم لتعيين رمز PIN وتحديث بياناتك.")
                    else:
                        st.error(msg)
    else:
        with st.form("register_form"):
            name = st.text_input("الاسم الكامل")
            phone = st.text_input("رقم الهاتف (مثال: 0797123456)")
            c1, c2 = st.columns(2)
            with c1:
                pin = st.text_input("اختر رمز PIN (4 أرقام)", type="password", max_chars=4)
            with c2:
                pin2 = st.text_input("أعد كتابة PIN", type="password", max_chars=4)
            address = st.text_area("عنوان التوصيل (المنطقة، الشارع، أقرب معلم)")
            map_link = st.text_input("رابط موقعك على خرائط جوجل (اختياري)")
            notes = st.text_input("ملاحظات لمندوب التوصيل (اختياري)")
            go = st.form_submit_button("إنشاء الحساب", use_container_width=True)
        if go:
            if not name.strip() or not address.strip():
                st.error("الاسم والعنوان مطلوبان.")
            elif not valid_phone(phone):
                st.error("رقم الهاتف غير صحيح (يجب أن يكون 07XXXXXXXX).")
            elif not valid_pin(pin) or pin != pin2:
                st.error("رمز PIN يجب أن يكون 4 أرقام ومتطابقًا في الخانتين.")
            else:
                existing = find_by_phone(sb, "customers", phone)
                if existing and existing.get("pin_hash"):
                    st.error("هذا الرقم مسجّل مسبقًا. استخدم «تسجيل دخول».")
                else:
                    try:
                        st.session_state.customer_name = name.strip()
                        st.session_state.customer_address = address.strip()
                        st.session_state.customer_map_link = map_link.strip()
                        st.session_state.delivery_notes = notes.strip()
                        st.session_state.customer_email = ""
                        np_ = norm_phone(phone)
                        pl = customer_payload(np_)
                        if existing:
                            sb.table("customers").update(pl).eq("id", existing["id"]).execute()
                            rid = existing["id"]
                        else:
                            rid = (sb.table("customers").insert(pl).execute().data or [{}])[0].get("id")
                        set_pin(sb, "customers", rid, np_, pin)
                        login_session(find_by_phone(sb, "customers", np_))
                        st.rerun()
                    except Exception as e:
                        st.error(f"تعذر إنشاء الحساب: {e}")


if not st.session_state.logged_in:
    render_auth()
    st.stop()


# ============================================================
# التوصيل + إرسال الطلب
# ============================================================
def customer_xy():
    if not st.session_state.customer_map_link:
        return None
    return customer_map_coords(st.session_state.customer_map_link)


def cart_subtotal(cart):
    return sum(safe_price(i.get("price")) * int(i.get("qty", 1)) for i in cart)


def compute_delivery(cart, xy):
    by_name = {m.get("name"): m for m in load_merchants()}
    total, uses_km = 0.0, False
    for mname in dict.fromkeys(i["merchant"] for i in cart):
        m = by_name.get(mname) or {}
        base = m.get("delivery_fee")
        fee = DEFAULT_BASE_FEE if base is None else safe_price(base)
        per_km = m.get("fee_per_km")
        per_km = DEFAULT_PER_KM if per_km is None else safe_price(per_km)
        if per_km > 0 and xy and GEO_OK:
            mc = merchant_coords(m)
            if mc:
                fee += per_km * route_info(mc[0], mc[1], xy[0], xy[1])["km"]
                uses_km = True
        total += fee
    return round(total, 2), uses_km


def wa_order_message(oid, cart, delivery, total, payment):
    lines = [f"طلب جديد رقم #{oid} - Halago", ""]
    for i in cart[:25]:
        lines.append(f"• {i['name']} ×{i.get('qty', 1)} — {safe_price(i['price']) * int(i.get('qty', 1)):.2f} د.أ ({i['merchant']})")
    if len(cart) > 25:
        lines.append(f"… و{len(cart) - 25} أصناف أخرى (التفاصيل في النظام)")
    lines += ["", f"التوصيل: {delivery:.2f} د.أ", f"الإجمالي: {total:.2f} د.أ", f"الدفع: {payment}", "",
              f"الاسم: {st.session_state.customer_name}", f"الهاتف: {st.session_state.phone}",
              f"العنوان: {st.session_state.customer_address}"]
    if st.session_state.customer_map_link:
        lines.append(f"الموقع: {st.session_state.customer_map_link}")
    return "\n".join(lines)


def place_order(cart, payment, delivery, xy, via_whatsapp=False):
    subtotal = cart_subtotal(cart)
    total = subtotal + delivery + SERVICE_FEE
    summary = "\n".join(
        f"- {i['name']} ×{i.get('qty', 1)} ({safe_price(i['price']) * int(i.get('qty', 1)):.2f} د.أ) [المتجر: {i['merchant']}]"
        for i in cart)
    summary += f"\nالتوصيل: {delivery:.2f} د.أ"
    addr = st.session_state.customer_address
    if st.session_state.delivery_notes:
        addr += f" (ملاحظات: {st.session_state.delivery_notes})"
    if st.session_state.customer_map_link:
        addr += f" | رابط الخريطة: {st.session_state.customer_map_link}"
    row = {
        "customer_name": st.session_state.customer_name,
        "customer_phone": st.session_state.phone,
        "customer_address": addr,
        "order_details": summary,
        "total_amount": round(total, 2),
        "payment_method": payment,
        "order_status": "قيد التجهيز",
        "driver_name": "",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    if xy:
        row["lat"], row["lng"] = xy
    try:
        res = sb.table("orders").insert(row).execute()
    except Exception:
        if "lat" not in row:
            raise
        row.pop("lat")
        row.pop("lng")
        res = sb.table("orders").insert(row).execute()
    oid = (res.data or [{}])[0].get("id")
    if PUSH_ON:
        try:
            send_push("admin", 0, "Halago", f"وصل طلب جديد رقم #{oid}")
        except Exception:
            pass
    telegram_ok, telegram_message = telegram_send(wa_order_message(oid, cart, delivery, total, payment))
    st.session_state["telegram_status"] = {
        "ok": telegram_ok,
        "message": telegram_message,
    }
    wa = None
    if via_whatsapp:
        wa = f"https://wa.me/{WA_NUMBER}?text=" + urllib.parse.quote(wa_order_message(oid, cart, delivery, total, payment))
    return oid, wa


def add_to_cart(pid, name, price, merchant):
    for i in st.session_state.cart:
        if i.get("pid") == pid and i["merchant"] == merchant:
            i["qty"] = int(i.get("qty", 1)) + 1
            return
    st.session_state.cart.append({"pid": pid, "name": name, "price": price, "merchant": merchant, "qty": 1})


def render_cart(prefix):
    st.markdown('<div class="kg-cart">', unsafe_allow_html=True)
    st.subheader("🛍 سلة الطلبات والفاتورة")

    last = st.session_state.get("last_order")
    if last:
        st.success(f"🎉 تم تأكيد طلبك رقم #{last['id']} وإرساله للنظام!")
        telegram_status = st.session_state.pop("telegram_status", None)
        if telegram_status:
            if telegram_status.get("ok"):
                st.caption("✅ تم إرسال نسخة من الطلب إلى تيليجرام.")
            else:
                st.warning(f"⚠️ لم يصل إشعار تيليجرام: {telegram_status.get('message')}")
        if last.get("wa"):
            st.link_button("📲 اضغط هنا لإرسال الطلب على واتساب أيضًا", last["wa"], use_container_width=True)
        if st.button("إغلاق", key=f"close_last_{prefix}"):
            st.session_state.last_order = None
            st.rerun()

    if not st.session_state.cart:
        st.info("السلة فارغة حالياً.")
    else:
        subtotal = cart_subtotal(st.session_state.cart)

        for ci, item in enumerate(st.session_state.cart):
            q = int(item.get("qty", 1))
            st.write(f"🔹 **{item['name']}** ×{q}")
            c1, c2, c3 = st.columns([2, 1, 1])
            with c1:
                st.caption(f"{item['merchant']} | {safe_price(item['price']) * q:.2f} د.أ")
            with c2:
                if st.button("➕", key=f"inc_{prefix}_{ci}"):
                    item["qty"] = q + 1
                    st.rerun()
            with c3:
                if st.button("➖", key=f"dec_{prefix}_{ci}"):
                    if q > 1:
                        item["qty"] = q - 1
                    else:
                        st.session_state.cart.pop(ci)
                    st.rerun()

        xy = customer_xy()
        delivery, uses_km = compute_delivery(st.session_state.cart, xy)
        total = subtotal + delivery + SERVICE_FEE

        st.markdown("---")
        st.write(f"🏷 **مجموع الأصناف:** {subtotal:.2f} د.أ")
        if subtotal < MIN_ORDER:
            remaining = MIN_ORDER - subtotal
            st.markdown(
                f"<div class='kg-cart-progress'>أضف <b>{remaining:.2f} د.أ</b> للوصول إلى الحد الأدنى وإتمام الطلب.</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                "<div class='kg-cart-progress'>✅ وصلت إلى الحد الأدنى — يمكنك إتمام طلبك الآن.</div>",
                unsafe_allow_html=True,
            )

        # ===== شريط التوصيل الأصفر =====
        st.markdown(
            f"<div class='kg-delivery-bar'>🛵 أجرة التوصيل: {delivery:.2f} د.أ</div>",
            unsafe_allow_html=True
        )
        if uses_km:
            st.caption("أجرة التوصيل = الأساسية + مبلغ حسب بُعد المتجر عن موقعك.")
        elif not xy:
            st.caption("تُحسب الأجرة الأساسية فقط لأن موقعك على الخريطة غير محدد.")

        st.write(f"⚙️ **الخدمة:** {SERVICE_FEE:.2f} د.أ")
        st.markdown(f"### 💰 الإجمالي النهائي: {total:.2f} د.أ")
        if not xy:
            st.warning("رابط موقعك على خرائط جوجل غير محدد أو غير صالح (من صفحة حسابي)، لن يرى السائق موقعك على الخريطة.")

        if st.button("🗑 تفريغ السلة", key=f"clear_cart_{prefix}", use_container_width=True):
            st.session_state.cart = []
            st.rerun()

        payment = st.radio(
            "اختر طريقة الدفع:",
            ["نقداً عند الاستلام", "CliQ (0797088219)", "Zain Cash"],
            key=f"pay_{prefix}_mode"
        )

        st.markdown("---")
        if subtotal < MIN_ORDER:
            st.warning(f"الحد الأدنى للطلب {MIN_ORDER:.2f} د.أ (قيمة الأصناف فقط). أضف أصنافًا بقيمة {MIN_ORDER - subtotal:.2f} د.أ لتتمكن من التأكيد.")
        else:
            for via_wa, label, key in ((False, "📌 تأكيد وإرسال للنظام", "submit"),
                                       (True, "💬 تأكيد وإرسال للنظام + واتساب", "submit_wa")):
                if st.button(label, key=f"{key}_{prefix}_mode", use_container_width=True):
                    try:
                        oid, wa = place_order(st.session_state.cart, payment, delivery, xy, via_wa)
                        st.session_state.last_order = {"id": oid, "wa": wa}
                        st.session_state.cart = []
                        st.rerun()
                    except Exception as e:
                        st.error(f"خطأ أثناء إرسال الطلب: {e}")

    st.markdown('</div>', unsafe_allow_html=True)

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
st.caption(f"👤 {st.session_state.customer_name}")
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

    cart_count = sum(int(item.get("qty", 1)) for item in st.session_state.cart)
    st.markdown(
        f"""
        <div class="kg-header">
            <div class="kg-location">📍 التوصيل إلى <b>{st.session_state.customer_address or 'عنوانك'}</b>　⌄</div>
            <div class="kg-home-title">🛒 Halago</div>
            <div class="kg-home-sub">كل ما تحتاجه من متاجر الكرك في مكان واحد</div>
            <div class="kg-search-hint">⌕　ابحث عن مطعم أو متجر أو صنف</div>
            <div style="color:#FFFFFF; margin-top:12px; font-size:13px;">🛍️ السلة: <b>{cart_count}</b> صنف</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # ============ شريط إعلانات متحرك مستمر ============
    st.markdown(
        """
        <div class="kg-promo">
            <div class="kg-marquee">
                <span class="kg-marquee-item">🎉 جاهز لتجربة نكهة جديدة؟ <b>عروض يومية</b></span>
                <span class="kg-marquee-item">🚚 اطلب الآن ووفر أكثر <b>توصيل سريع</b></span>
                <span class="kg-marquee-item">🏬 متاجر الكرك بين يديك <b>اكتشف الآن</b></span>
                <span class="kg-marquee-item">🎉 جاهز لتجربة نكهة جديدة؟ <b>عروض يومية</b></span>
                <span class="kg-marquee-item">🚚 اطلب الآن ووفر أكثر <b>توصيل سريع</b></span>
                <span class="kg-marquee-item">🏬 متاجر الكرك بين يديك <b>اكتشف الآن</b></span>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    all_merchants = load_merchants()

    if st.session_state.selected_merchant:
        mname = st.session_state.selected_merchant
        m_data = next((m for m in all_merchants if m.get("name") == mname), {"name": mname, "category": "", "location": "", "map_link": ""})

        if st.button("⬅ العودة إلى قائمة المتاجر والأقسام"):
            st.session_state.selected_merchant = None
            st.session_state.store_q = ""
            st.session_state.store_page = 0
            st.rerun()

        left_m, right_m = st.columns([2.2, 1], gap="large")

        with left_m:
            st.markdown(f"""
            <div style="background:white; border-radius:16px; padding:20px; margin-bottom:15px; border:1px solid #E2E8F0; box-shadow:0 4px 15px rgba(0,0,0,0.03); display:flex; align-items:center; gap:15px;">
                <div>
                    <div style="font-size:24px; font-weight:900; color:#E64A19;">🏬 {mname}</div>
                    <div style="font-size:13px; color:#64748B; margin-top:4px;">التصنيف: <b>{m_data.get('category','')}</b> | الموقع: {m_data.get('location','')}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # ===== تقييم المتجر (نجوم) =====
            render_rating(m_data)

            if m_data.get("map_link"):
                st.markdown(f'<a href="{m_data.get("map_link")}" target="_blank" style="color:#E64A19; font-weight:bold; text-decoration:none; display:inline-block; margin-bottom:15px;">🗺 فتح موقع المتجر على خرائط جوجل</a>', unsafe_allow_html=True)

            sq = st.text_input("🔎 ابحث عن صنف داخل هذا المتجر...", value=st.session_state.store_q, key="store_q_input")
            if sq.strip() != st.session_state.store_q:
                st.session_state.store_q = sq.strip()
                st.session_state.store_page = 0
                st.rerun()

            store_products, total_count = load_products(mname, st.session_state.store_q, st.session_state.store_page)
            pages = max(1, -(-total_count // PAGE_SIZE))
            if st.session_state.store_page >= pages:
                st.session_state.store_page = pages - 1

            if store_products:
                st.subheader(f"📋 قائمة الأصناف المتوفرة ({total_count} صنف)")

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
                        st.caption(f"{quantity} {unit} | <span style='color:#E64A19; font-weight:bold; font-size:14px;'>{price:.2f} د.أ</span>", unsafe_allow_html=True)

                    with p_col3:
                        st.markdown("<br>", unsafe_allow_html=True)
                        if st.button("➕ إضافة للسلة", key=f"add_store_p_{pi}_{p['id']}", use_container_width=True):
                            add_to_cart(p["id"], f"{item_name} ({quantity} {unit})", price, mname)
                            st.toast(f"تمت إضافة {item_name} إلى السلة!")
                            st.rerun()

                    st.markdown("<hr style='margin:10px 0; border:0; border-top:1px solid #F1F5F9;'>", unsafe_allow_html=True)

                if pages > 1:
                    pg1, pg2, pg3 = st.columns([1, 2, 1])
                    with pg1:
                        if st.session_state.store_page > 0 and st.button("◀ السابق", key="prev_pg", use_container_width=True):
                            st.session_state.store_page -= 1
                            st.rerun()
                    with pg2:
                        st.markdown(f"<div style='text-align:center; padding-top:10px;'>صفحة {st.session_state.store_page + 1} من {pages}</div>", unsafe_allow_html=True)
                    with pg3:
                        if st.session_state.store_page < pages - 1 and st.button("التالي ▶", key="next_pg", use_container_width=True):
                            st.session_state.store_page += 1
                            st.rerun()
            else:
                if st.session_state.store_q:
                    st.info("لا توجد أصناف مطابقة لبحثك في هذا المتجر.")
                else:
                    st.info("لا توجد أصناف مضافة لهذا المتجر حتى الآن.")

        with right_m:
            render_cart("store")

    else:
        user_input = st.text_input(
            "🔍 ابحث عن متجر أو صنف (اكتب الحروف الأولى)...",
            value=st.session_state.search_query,
            key=f"user_search_box_{st.session_state.search_input_key}"
        )

        if user_input != st.session_state.search_query:
            st.session_state.search_query = user_input

        st.markdown("<div class='kg-section-title'>استكشف الأقسام</div>", unsafe_allow_html=True)

        # ===== بطاقات الأقسام (مصغّرة) =====
        cols_per_row = 4
        for i in range(0, len(categories), cols_per_row):
            row_cats = categories[i:i + cols_per_row]
            c_cols = st.columns(len(row_cats))
            for j, cat in enumerate(row_cats):
                c_name = cat["name"]
                c_img = cat["image"]
                is_sel = (st.session_state.selected_category == c_name)
                sel_class = "kg-sel" if is_sel else ""

                with c_cols[j]:
                    st.markdown(
                        f"""
                        <div class="kg-cat-card {sel_class}">
                            <img src="{c_img}">
                            <div class="kg-cat-name">{c_name}</div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                    btn_label = f"✓ {c_name}" if is_sel else f"عرض {c_name}"
                    if st.button(btn_label, key=f"cat_card_{i+j}", use_container_width=False):
                        st.session_state.selected_category = c_name
                        st.query_params["cat"] = c_name
                        st.session_state.search_query = ""
                        st.session_state.search_input_key += 1
                        st.rerun()

        left, right = st.columns([2.2, 1], gap="large")

        with left:
            st.markdown("<div class='kg-section-title'>المتاجر القريبة منك</div>", unsafe_allow_html=True)

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
                matching_merchants_by_product = merchants_with_product(current_search)

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
                    badge = html.escape(merchant_badge(store))
                    eta = html.escape(merchant_eta(store))
                    fee_value = store.get("delivery_fee")
                    fee_text = f"من {safe_price(fee_value):.2f} د.أ" if fee_value is not None else "تحسب حسب الموقع"

                    with s_cols[sj]:
                        st.markdown('<div class="kg-store-card">', unsafe_allow_html=True)
                        display_image(store.get("image_data"), width=90, fallback="🏬")
                        st.markdown(f"<div style='font-size:18px; font-weight:900; margin:10px 0 4px 0;'>{html.escape(str(sname))}</div>", unsafe_allow_html=True)
                        st.markdown(f"<span class='kg-store-badge'>✓ {badge}</span>", unsafe_allow_html=True)
                        st.markdown(
                            f"<div class='kg-store-meta'>📍 {html.escape(str(scat))} • {html.escape(str(sloc))}<br>"
                            f"🚚 وقت تقديري: <b>{eta}</b> • رسوم التوصيل: <b>{fee_text}</b></div>",
                            unsafe_allow_html=True,
                        )

                        # ===== تقييم المتجر =====
                        render_rating(store)

                        if st.button(f"🛒 تصفح أصناف {sname}", key=f"enter_store_{mi+sj}", use_container_width=True):
                            st.session_state.selected_merchant = sname
                            st.session_state.store_q = current_search if current_search else ""
                            st.session_state.store_page = 0
                            st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)

        with right:
            render_cart("main")


# ============================================================
# 2. الطلبات وتتبع الرحلة
# ============================================================
elif st.session_state.nav_tab == "الطلبات":
    maybe_autorefresh()
    st.markdown(
        """
        <div class="kg-header">
            <div class="kg-header-title">📦 طلباتي ومتابعة رحلة التوصيل</div>
            <div class="kg-header-sub">تابع حالة طلبك خطوة بخطوة من التجهيز وحتى الوصول</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    try:
        orders = sb.table("orders").select("*").eq("customer_phone", st.session_state.phone).order("id", desc=True).execute().data or []
        if orders:
            for ord_item in orders:
                status = ord_item.get('order_status', 'قيد التجهيز')
                driver = ord_item.get('driver_name', '')

                steps = ["قيد التجهيز", "جاهز للاستلام", "في الطريق", "تم التوصيل"]
                status_to_idx = {
                    "قيد التجهيز": 0, "جاهز": 1, "جاهز للاستلام": 1,
                    "جاري التوصيل": 2, "في الطريق": 2, "تم التوصيل": 3, "تم الاستلام": 3,
                }
                current_step_idx = status_to_idx.get(status, 0)

                st.markdown(f"""
                <div style="background:white; border-radius:16px; padding:20px; margin-bottom:15px; border:1px solid #E2E8F0; box-shadow: 0 4px 15px rgba(0,0,0,0.03);">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                        <span style="font-size:16px; font-weight:900; color:#E64A19;">رقم الطلب: #{ord_item.get('id')}</span>
                        <span style="background:#FFF3EE; color:#E64A19; padding:4px 10px; border-radius:20px; font-weight:bold; font-size:12px;">الحالة: {status}</span>
                    </div>
                    <p style="margin:5px 0; font-size:13px; color:#64748B;"><b>وقت الطلب:</b> {ord_item.get('created_at')}</p>
                    <p style="margin:5px 0; font-size:13px; color:#64748B;"><b>المبلغ الإجمالي:</b> {ord_item.get('total_amount')} د.أ</p>
                    <hr style="margin:10px 0; border:0; border-top:1px solid #F1F5F9;">
                """, unsafe_allow_html=True)

                st.markdown("📍 **رحلة الطلب المباشرة:**")
                prog_cols = st.columns(4)
                for s_idx, s_name in enumerate(steps):
                    with prog_cols[s_idx]:
                        if s_idx <= current_step_idx:
                            st.markdown(f"<div style='background:#E64A19; color:white; padding:6px; border-radius:8px; text-align:center; font-size:11px; font-weight:bold;'>✓ {s_name}</div>", unsafe_allow_html=True)
                        else:
                            st.markdown(f"<div style='background:#F1F5F9; color:#94A3B8; padding:6px; border-radius:8px; text-align:center; font-size:11px;'>{s_name}</div>", unsafe_allow_html=True)

                if current_step_idx >= 1 or driver:
                    st.markdown("<br>", unsafe_allow_html=True)
                    col_d1, col_d2 = st.columns(2)
                    with col_d1:
                        driver_display = driver if driver else "جارٍ تعيين سائق..."
                        st.markdown(f"🛵 **السائق المسؤول:** `{driver_display}`")
                    with col_d2:
                        st.markdown("⏱ **الوقت المتوقع للوصول:** `خلال 15-20 دقيقة`")

                if st.session_state.customer_map_link:
                    st.markdown(f'<div style="margin-top:10px;"><a href="{st.session_state.customer_map_link}" target="_blank" style="background:#0F172A; color:white; padding:6px 12px; border-radius:6px; font-size:12px; text-decoration:none; display:inline-block;">🗺 عرض موقع تسليم الطلب على خرائط جوجل</a></div>', unsafe_allow_html=True)

                with st.expander("📄 تفاصيل الأصناف المطلوبة"):
                    st.code(ord_item.get('order_details', ''), language=None)

                st.markdown("</div>", unsafe_allow_html=True)
        else:
            info_col1, info_col2 = st.columns([4, 1])
            with info_col1:
                st.info("لا توجد طلبات سابقة مسجلة برقم هاتفك الحالي.")
            with info_col2:
                if st.button("🔄 تحديث الطلبات", use_container_width=True):
                    st.rerun()
    except Exception as e:
        st.error(f"تعذر جلب الطلبات: {e}")


# ============================================================
# 3. الحساب وعنوان التوصيل
# ============================================================
elif st.session_state.nav_tab == "الحساب":
    st.markdown(
        """
        <div class="kg-header">
            <div class="kg-header-title">👤 حسابي وعنوان التوصيل</div>
            <div class="kg-header-sub">حدّث معلوماتك وموقعك على خرائط جوجل ليصلك الطلب بدقة</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.info(f"📞 رقم الهاتف: {st.session_state.phone}  (لتغيير الرقم أنشئ حسابًا جديدًا)")

    with st.form("account_form"):
        a_name = st.text_input("اسمك الكريم:", value=st.session_state.customer_name)
        a_email = st.text_input("البريد الإلكتروني (اختياري):", value=st.session_state.customer_email)
        a_addr = st.text_area("عنوان التوصيل (المنطقة، الشارع، أقرب معلم):", value=st.session_state.customer_address)
        a_notes = st.text_area("ملاحظات خاصة لمندوب التوصيل:", value=st.session_state.delivery_notes)
        st.markdown("📍 **الموقع الجغرافي (رابط خرائط جوجل):**")
        a_link = st.text_input("رابط موقعك على خرائط جوجل (Google Maps URL):", value=st.session_state.customer_map_link)
        save_btn = st.form_submit_button("💾 حفظ وتحديث البيانات", use_container_width=True)

    if save_btn:
        if not a_name.strip() or not a_addr.strip():
            st.error("الاسم والعنوان مطلوبان.")
        else:
            try:
                st.session_state.customer_name = a_name.strip()
                st.session_state.customer_email = a_email.strip()
                st.session_state.customer_address = a_addr.strip()
                st.session_state.delivery_notes = a_notes.strip()
                st.session_state.customer_map_link = a_link.strip()
                sb.table("customers").update(customer_payload(st.session_state.phone)).eq("id", st.session_state.customer_id).execute()
                st.success("🎉 تم حفظ بياناتك بنجاح!")
            except Exception as e:
                st.error(f"خطأ أثناء الحفظ: {e}")

    if st.session_state.customer_map_link:
        st.markdown(f'<div style="margin:10px 0; padding:10px; background:#FFF8F5; border:1px solid #FF5722; border-radius:8px;"><a href="{st.session_state.customer_map_link}" target="_blank" style="color:#E64A19; font-weight:bold; text-decoration:none;">🗺 معاينة موقعك المسجل على خرائط جوجل</a></div>', unsafe_allow_html=True)
        if customer_xy():
            st.caption("✅ تم التعرّف على إحداثيات موقعك، وسيظهر للسائق على الخريطة.")
        else:
            st.caption("⚠️ لم نستطع قراءة الإحداثيات من هذا الرابط. استخدم مشاركة الموقع من خرائط Google أو رابطًا يحتوي على دبوس الموقع.")

    map_cols = st.columns(2)
    with map_cols[0]:
        st.link_button("🌐 افتح خرائط جوجل لنسخ الرابط", "https://maps.google.com", use_container_width=True)
    with map_cols[1]:
        if st.button("📍 تعيين موقع افتراضي (الكرك - المرج)", use_container_width=True):
            st.session_state.customer_map_link = "https://maps.google.com/?q=31.1818,35.7011"
            try:
                sb.table("customers").update(customer_payload(st.session_state.phone)).eq("id", st.session_state.customer_id).execute()
            except Exception:
                pass
            st.rerun()

    with st.expander("🔐 تغيير رمز PIN"):
        with st.form("pin_change_form"):
            old_pin = st.text_input("PIN الحالي", type="password", max_chars=4)
            new_pin = st.text_input("PIN الجديد (4 أرقام)", type="password", max_chars=4)
            go_pin = st.form_submit_button("تغيير PIN")
        if go_pin:
            row = find_by_phone(sb, "customers", st.session_state.phone)
            ok, msg = check_pin(sb, "customers", row, old_pin) if row else (False, "الحساب غير موجود")
            if not ok:
                st.error(msg if msg != NO_PIN else "لا يوجد PIN حالي.")
            elif not valid_pin(new_pin):
                st.error("PIN الجديد يجب أن يكون 4 أرقام.")
            else:
                set_pin(sb, "customers", row["id"], row["phone"], new_pin)
                st.success("تم تغيير PIN بنجاح.")

    col_b1, col_b2 = st.columns(2)
    with col_b1:
        if st.button("🚪 تسجيل الخروج", use_container_width=True):
            for k in ("logged_in", "customer_id", "phone", "customer_name", "customer_email", "customer_address",
                      "delivery_notes", "customer_map_link", "cart", "last_order"):
                st.session_state.pop(k, None)
            st.session_state.nav_tab = "الرئيسية"
            st.rerun()
    with col_b2:
        with st.expander("🗑 حذف حسابي نهائيًا"):
            del_pin = st.text_input("أدخل PIN لتأكيد الحذف", type="password", max_chars=4, key="del_pin")
            if st.button("حذف الحساب نهائيًا", use_container_width=True):
                row = find_by_phone(sb, "customers", st.session_state.phone)
                ok, msg = check_pin(sb, "customers", row, del_pin) if row else (False, "الحساب غير موجود")
                if ok:
                    sb.table("customers").delete().eq("id", row["id"]).execute()
                    for k in ("logged_in", "customer_id", "phone", "customer_name", "customer_email", "customer_address",
                              "delivery_notes", "customer_map_link", "cart", "last_order"):
                        st.session_state.pop(k, None)
                    st.rerun()
                else:
                    st.error("رمز PIN غير صحيح.")
