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
import hashlib
import hmac
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

# ---- الدخول برقم الهاتف فقط (بدون رمز PIN) ----
try:
    from auth_pin import valid_phone, norm_phone, find_by_phone
except Exception:
    def norm_phone(phone):
        digits = re.sub(r"\D", "", str(phone or ""))
        if digits.startswith("00962"):
            digits = "0" + digits[5:]
        elif digits.startswith("962"):
            digits = "0" + digits[3:]
        if digits and not digits.startswith("0"):
            digits = "0" + digits
        return digits

    def valid_phone(phone):
        return bool(re.fullmatch(r"07\d{8}", norm_phone(phone)))

    def find_by_phone(sb, table, phone):
        target = norm_phone(phone)
        if not target:
            return None
        try:
            rows = sb.table(table).select("*").execute().data or []
        except Exception:
            return None
        for row in rows:
            if norm_phone(row.get("phone")) == target:
                return row
        return None

try:
    from streamlit_cookies_controller import CookieController
    COOKIE_CONTROLLER_OK = True
except Exception:
    CookieController = None
    COOKIE_CONTROLLER_OK = False

try:
    import folium
    from streamlit_folium import st_folium
    MAP_PICKER_OK = True
except Exception:
    folium = None
    st_folium = None
    MAP_PICKER_OK = False


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

# كوبونات محلية قابلة للتعديل، ولا تحتاج إلى جدول جديد في Supabase.
COUPONS = {
    "HALAGO10": {"type": "percent", "value": 10, "label": "خصم 10%"},
    "WELCOME": {"type": "fixed", "value": 1.0, "label": "خصم 1.00 د.أ"},
}

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

cookie_controller = None
if COOKIE_CONTROLLER_OK:
    try:
        if "cookie_controller" not in st.session_state:
            st.session_state["cookie_controller"] = CookieController()
        cookie_controller = st.session_state["cookie_controller"]
    except Exception:
        cookie_controller = None


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
    padding-bottom: 6.5rem !important;
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

/* ============ بطاقات الأقسام (دائرية بدون خلفية مستطيلة) ============ */
.kg-cat-card {
    background: transparent;
    border: 0;
    border-radius: 0;
    padding: 0;
    text-align: center;
    margin: 0 auto 4px;
    width: 100%;
    box-sizing: border-box;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
}
.kg-cat-card img {
    width: 64px !important;
    height: 64px !important;
    object-fit: cover;
    border-radius: 50%;
    margin-bottom: 6px;
    border: 2px solid #FFFFFF;
    background: #FFF7F0;
    box-shadow: 0 3px 10px rgba(0,0,0,.10);
}
.kg-cat-card.kg-sel img {
    border-color: #FF5722;
    box-shadow: 0 0 0 3px rgba(255,87,34,.18);
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
/* اسم القسم أسفل الصورة — نص شفاف بدون أي إطار أو خلفية (نمط طلبات) */
div[data-testid="column"]:has(.kg-cat-card) div[data-testid="stButton"] {
    width: 100% !important;
    max-width: 100% !important;
    margin: -2px 0 0 !important;
}
div[data-testid="column"]:has(.kg-cat-card) .stButton > button,
div[data-testid="column"]:has(.kg-cat-card) .stButton > button:hover,
div[data-testid="column"]:has(.kg-cat-card) .stButton > button:focus,
div[data-testid="column"]:has(.kg-cat-card) .stButton > button:active {
    width: 100% !important;
    min-width: 0 !important;
    max-width: 100% !important;
    min-height: 0 !important;
    height: auto !important;
    padding: 0 !important;
    margin: 0 !important;
    background: transparent !important;
    color: #2D3142 !important;
    border: 0 !important;
    border-radius: 0 !important;
    box-shadow: none !important;
    font-size: 11px !important;
    font-weight: 800 !important;
    line-height: 1.3 !important;
    text-align: center !important;
}
div[data-testid="column"]:has(.kg-cat-card) .stButton > button p {
    font-size: 11px !important;
    font-weight: 800 !important;
    color: inherit !important;
    margin: 0 !important;
    white-space: normal !important;
    line-height: 1.25 !important;
}
div[data-testid="column"]:has(.kg-cat-card.kg-sel) .stButton > button {
    color: #FF5722 !important;
}

/* ============ شبكة الأقسام: 4 في الصف حتى على الهاتف (نمط طلبات) ============ */
div[data-testid="stHorizontalBlock"]:has(.kg-cat-card) { flex-wrap: nowrap !important; gap: 8px !important; margin-bottom: 8px; }
div[data-testid="stHorizontalBlock"]:has(.kg-cat-card) > div {
    min-width: 0 !important; width: auto !important; flex: 1 1 0 !important;
    background: #FBF3EA; border-radius: 16px; padding: 10px 2px 8px;
}
div[data-testid="stHorizontalBlock"]:has(.kg-cat-card) > div:has(.kg-cat-card.kg-sel) { background: #FFEFE5; box-shadow: inset 0 0 0 2px #FF5722; }
div[data-testid="stHorizontalBlock"] .kg-cat-card img {
    width: 58px !important; height: 58px !important; border-radius: 16px !important;
    border: 0 !important; box-shadow: none !important; background: transparent !important; margin-bottom: 4px;
}
div[data-testid="stHorizontalBlock"]:has(.kg-cat-card) > div > div { gap: 2px !important; }
div[class*="st-key-cat_card_"] button p { min-height: 28px; display: flex; align-items: center; justify-content: center; }

/* ============ اسم القسم تحت الصورة (بالوسط، بدون إطار) ============ */
div[class*="st-key-cat_card_"] { width: 100% !important; display: flex !important; justify-content: center !important; }
div[class*="st-key-cat_card_"] div[data-testid="stButton"] { width: auto !important; display: flex; justify-content: center; }
div[class*="st-key-cat_card_"] button, div[class*="st-key-cat_card_"] button:hover,
div[class*="st-key-cat_card_"] button:focus, div[class*="st-key-cat_card_"] button:active {
    background: transparent !important; border: 0 !important; box-shadow: none !important; outline: none !important;
    padding: 0 !important; margin: 0 auto !important; min-height: 0 !important; width: auto !important; height: auto !important;
}
div[class*="st-key-cat_card_"] button p { color: #2D3142 !important; font-size: 12px !important; font-weight: 800 !important; margin: 0 !important; text-align: center !important; }
div[class*="st-key-cat_card_"] button:hover p { color: #FF5722 !important; }
div[class*="st-key-cat_card_sel_"] button p { color: #FF5722 !important; }
div[class*="st-key-clear_search_btn"] button {
    background: #FFF3EE !important; color: #E64A19 !important; border: 1px solid #FFD2C0 !important;
    border-radius: 22px !important; min-height: 36px !important; font-weight: 800 !important; box-shadow: none !important;
}
div[class*="st-key-clear_search_btn"] button p { color: inherit !important; margin: 0 !important; }

/* ============ بطاقة المتجر (نمط طلبات) ============ */
div[class*="st-key-store_card_"] {
    background: #FFFFFF; border: 1px solid #EEF0F2; border-radius: 18px;
    padding: 12px; margin-bottom: 14px; box-shadow: 0 2px 10px rgba(0,0,0,.04);
    transition: border-color .2s ease, box-shadow .2s ease;
}
div[class*="st-key-store_card_"]:hover { border-color: #FFB89C; box-shadow: 0 6px 18px rgba(255,87,34,.10); }
div[class*="st-key-store_card_"] div[data-testid="stImage"] { width: 100% !important; }
div[class*="st-key-store_card_"] img {
    width: 100% !important; height: 104px !important; object-fit: cover !important;
    border-radius: 14px !important; background: #FFF7F0;
}
.kg-sc-name { font-size: 17px; font-weight: 900; color: #202124 !important; line-height: 1.3; }
.kg-sc-sub { font-size: 12px; color: #6B7280 !important; margin-top: 3px; }
.kg-sc-meta { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; margin-top: 9px; }
.kg-sc-meta span { font-size: 12px; font-weight: 700; color: #4B5563 !important; }
.kg-pill { border-radius: 20px; padding: 2px 9px; }
.kg-pill-rate { background: #FFF6DB; color: #B45309 !important; }
.kg-pill-new { background: #E8F5E9; color: #2E7D32 !important; }
.kg-pill-hot { background: #FFF0E6; color: #D84315 !important; }
.kg-sc-badge { margin-top: 8px; font-size: 11px; font-weight: 800; color: #2E7D32 !important; }
div[class*="st-key-enter_store_"] button {
    background: #FFF3EE !important; color: #E64A19 !important; border: 1px solid #FFD2C0 !important;
    border-radius: 12px !important; min-height: 38px !important; font-weight: 800 !important;
    box-shadow: none !important; margin-top: 6px !important;
}
div[class*="st-key-enter_store_"] button p { color: inherit !important; margin: 0 !important; }
div[class*="st-key-enter_store_"] button:hover { background: #FF5722 !important; color: #FFFFFF !important; border-color: #FF5722 !important; }
.kg-section-count { font-size: 13px; font-weight: 700; color: #6B7280 !important; margin-right: 6px; }

/* ============ السلة (نمط طلبات) ============ */
.kg-cart-head { background: #FFFFFF; border: 1px solid #F1F1F1; border-radius: 16px; padding: 14px 16px; margin-bottom: 6px; }
.kg-cart-title { font-size: 20px; font-weight: 900; color: #202124 !important; }
.kg-cart-count { font-size: 13px; color: #6B7280 !important; padding-top: 6px; }
.kg-cart-item { background: #FFFFFF; border: 1px solid #F4F4F5; border-radius: 14px; padding: 12px 14px; margin: 8px 0 4px; }
.kg-cart-item-name { font-size: 15px; font-weight: 800; color: #202124 !important; }
.kg-cart-item-sub { font-size: 12px; color: #6B7280 !important; margin-top: 3px; }
.kg-qty { text-align: center; font-size: 16px; font-weight: 900; color: #202124 !important; padding-top: 5px; }
div[class*="st-key-inc_"] button, div[class*="st-key-dec_"] button { border-radius: 12px !important; min-height: 34px !important; font-weight: 900 !important; }

/* ============ بطاقة المتجر (نمط طلبات) ============ */
.kg-store-row { font-size: 12px; color: #4B5563 !important; font-weight: 700; margin-top: 7px; }
.kg-dot { color: #D1D5DB !important; margin: 0 5px; }

/* ============ ترحيب + الموقع (نمط طلبات) ============ */
.kg-greet { margin: 8px 0 4px; }
.kg-greet-loc { font-size: 12px; font-weight: 800; color: #F4510B !important; }
.kg-greet-title { font-size: 24px; font-weight: 900; color: #202124 !important; margin-top: 5px; }
.kg-greet-sub { font-size: 14px; color: #6B7280 !important; margin-top: 3px; }
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
    .kg-cat-card img { width:56px !important; height:56px !important; border-radius:50%; margin-bottom:4px; }
    .kg-greet-title { font-size:20px; }
    .kg-promo { height:52px; border-radius:13px; }
    .kg-marquee-item { font-size:13px; margin-right:55px; }
}

/* ============ شاشة الدخول (نمط طلبات) ============ */
.kg-auth-hero { text-align: center; padding: 46px 0 8px; }
.kg-auth-logo { font-size: 76px; line-height: 1; }
.kg-auth-name { font-size: 40px; font-weight: 900; color: #F4510B !important; letter-spacing: 1px; margin-top: 6px; }
.kg-auth-tag { font-size: 15px; color: #374151 !important; margin-top: 6px; }
.kg-auth-card { background: #FFFFFF; border: 1px solid #F1F1F1; border-radius: 18px; padding: 16px 16px 8px; margin: 18px auto 10px; max-width: 520px; box-shadow: 0 8px 24px rgba(0,0,0,.05); text-align: center; }
.kg-auth-cardtitle { font-size: 18px; font-weight: 900; color: #202124 !important; }
.kg-auth-sub { font-size: 13px; color: #6B7280 !important; margin-top: 5px; padding-bottom: 10px; }

/* ============ بطاقة المستخدم ============ */
.kg-user-chip { display: inline-block; background: #FFF3EE; color: #D84315 !important; border-radius: 20px; padding: 5px 14px; font-size: 12px; font-weight: 800; margin: 2px 0 8px; }

/* ============ عروض وبانرات (نمط طلبات) ============ */
.kg-offer-card { border-radius: 16px; padding: 14px 16px; min-height: 118px; color: #FFFFFF !important; box-shadow: 0 6px 16px rgba(0,0,0,.10); margin-bottom: 8px; display: flex; flex-direction: column; justify-content: center; }
.kg-offer-card.o1 { background: linear-gradient(135deg,#FF5722 0%,#FF8A50 100%); }
.kg-offer-card.o2 { background: linear-gradient(135deg,#7B1FA2 0%,#AB47BC 100%); }
.kg-offer-card.o3 { background: linear-gradient(135deg,#0B3D91 0%,#1976D2 100%); }
.kg-offer-card .kg-offer-title { font-size: 17px; font-weight: 900; color: #FFFFFF !important; }
.kg-offer-card .kg-offer-sub { font-size: 12px; color: #FFFFFF !important; opacity: .92; margin-top: 5px; }
.kg-offer-card .kg-offer-tag { display: inline-block; margin-top: 9px; background: rgba(255,255,255,.22); border-radius: 20px; padding: 3px 10px; font-size: 11px; font-weight: 800; color: #FFFFFF !important; width: fit-content; }

/* ============ شريط سفلي (نمط طلبات) ============ */
.kg-bottom-nav { position: fixed; left: 0; right: 0; bottom: 0; height: 62px; background: #FFFFFF; border-top: 1px solid #EFEFEF; box-shadow: 0 -4px 14px rgba(0,0,0,.05); z-index: 9000; }
div[class*="st-key-nav_home"], div[class*="st-key-nav_orders"], div[class*="st-key-nav_account"] { position: fixed; bottom: 9px; width: 30%; max-width: 180px; z-index: 9999; }
div[class*="st-key-nav_home"] { left: 3%; }
div[class*="st-key-nav_orders"] { left: 35%; }
div[class*="st-key-nav_account"] { left: 67%; }
div[class*="st-key-nav_home"] button, div[class*="st-key-nav_orders"] button, div[class*="st-key-nav_account"] button {
    background: transparent !important; color: #FF5722 !important; border: 0 !important;
    box-shadow: none !important; font-size: 12px !important; font-weight: 800 !important; min-height: 34px !important;
}

/* ============ شريط البحث المستدير ============ */
div[class*="st-key-user_search_box_"] input, div[class*="st-key-store_q_input"] input {
    border-radius: 26px !important; background: #F6F6F6 !important; border: 1px solid #ECECEC !important;
    padding: 12px 18px !important; font-size: 15px !important;
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
                    background:linear-gradient(135deg,#E94B10 0%,#FF7A21 100%);">
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
    "cart": [], "coupon_code": "", "remember_me": False, "nav_tab": "الرئيسية", "search_query": "", "search_input_key": 0,
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


def render_customer_location_picker():
    """خريطة يضغط عليها العميل لتحديد موقع التسليم وحفظه كرابط Google Maps."""
    if not MAP_PICKER_OK:
        st.warning("خريطة تحديد الموقع تحتاج تثبيت folium و streamlit-folium من requirements.txt.")
        return
    current = customer_map_coords(st.session_state.customer_map_link)
    center = list(current) if current else [31.1818, 35.7011]
    fmap = folium.Map(location=center, zoom_start=15 if current else 12, control_scale=True)
    if current:
        folium.Marker(
            location=list(current),
            tooltip="موقع التسليم المحفوظ",
            popup="موقع الزبون",
            icon=folium.Icon(color="red", icon="home"),
        ).add_to(fmap)
    result = st_folium(fmap, height=300, width=None, key="customer_location_picker", returned_objects=["last_clicked"])
    clicked = (result or {}).get("last_clicked") or {}
    if clicked.get("lat") is not None and clicked.get("lng") is not None:
        lat, lng = float(clicked["lat"]), float(clicked["lng"])
        st.session_state["pending_customer_location"] = (lat, lng)
    pending = st.session_state.get("pending_customer_location")
    if pending:
        lat, lng = pending
        st.success(f"تم تحديد الموقع: {lat:.6f}, {lng:.6f}")
        if st.button("📍 حفظ الموقع المحدد", key="save_picked_location", use_container_width=True):
            st.session_state.customer_map_link = f"https://maps.google.com/?q={lat:.7f},{lng:.7f}"
            try:
                sb.table("customers").update(customer_payload(st.session_state.phone)).eq("id", st.session_state.customer_id).execute()
                st.session_state.pop("pending_customer_location", None)
                st.success("✅ تم حفظ موقع التسليم بنجاح.")
                st.rerun()
            except Exception as exc:
                st.error(f"تعذر حفظ الموقع: {exc}")


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


def coupon_discount(code, subtotal):
    """حساب الخصم محليًا، دون حفظ الكوبون أو تعديل أي بيانات في Supabase."""
    normalized = str(code or "").strip().upper()
    coupon = COUPONS.get(normalized)
    if not coupon or subtotal <= 0:
        return 0.0, None
    if coupon["type"] == "percent":
        discount = subtotal * float(coupon["value"]) / 100
    else:
        discount = float(coupon["value"])
    return round(min(discount, subtotal), 2), coupon


@st.cache_data(ttl=120, show_spinner=False)
def load_popular_merchants():
    """قراءة فقط: يحسب شعبية المتاجر من تفاصيل الطلبات الموجودة."""
    try:
        rows = sb.table("orders").select("order_details").limit(5000).execute().data or []
        counts = {}
        for row in rows:
            details = str(row.get("order_details") or "")
            for merchant in re.findall(r"\[المتجر:\s*(.*?)\]", details):
                name = merchant.strip()
                if name:
                    counts[name] = counts.get(name, 0) + 1
        merchants = {str(m.get("name")): m for m in load_merchants()}
        ranked = sorted(counts.items(), key=lambda pair: pair[1], reverse=True)
        return [(merchants[name], count) for name, count in ranked if name in merchants][:6]
    except Exception:
        return []


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
    addr = row.get("address") or row.get("customer_address") or ""
    notes = row.get("delivery_notes") or row.get("notes") or ""
    link = row.get("map_link") or row.get("customer_map_link") or ""
    if "رابط الخريطة:" in addr or "(ملاحظات:" in addr:
        l_addr, l_notes, l_link = legacy_split(addr)
        addr, notes, link = l_addr, notes or l_notes, link or l_link
    st.session_state.update({
        "logged_in": True, "customer_id": row.get("id"), "phone": row.get("phone") or "",
        "customer_name": row.get("name") or row.get("customer_name") or "", "customer_address": addr,
        "delivery_notes": notes, "customer_map_link": link, "customer_email": row.get("email") or "",
    })


def _session_secret():
    return _setting_value("APP_SESSION_SECRET") or SUPABASE_ANON_KEY


def remember_customer(phone):
    """يحفظ رمز جلسة موقّعًا، وليس رقم PIN، في متصفح العميل."""
    if not cookie_controller:
        return
    try:
        expires = int(time.time()) + 30 * 24 * 60 * 60
        payload = f"{norm_phone(phone)}|{expires}"
        signature = hmac.new(_session_secret().encode(), payload.encode(), hashlib.sha256).hexdigest()
        token = base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=") + "." + signature
        cookie_controller.set("halago_customer_session", token, max_age=30 * 24 * 60 * 60)
    except Exception:
        pass


def restore_customer_session():
    if st.session_state.get("logged_in") or not cookie_controller:
        return
    try:
        # يحدّث نسخة الكوكيز من المتصفح بعد إعادة فتح الصفحة.
        cookie_controller.refresh()
        token = cookie_controller.get("halago_customer_session")
        if not token or "." not in str(token):
            return
        encoded, signature = str(token).rsplit(".", 1)
        padded = encoded + "=" * (-len(encoded) % 4)
        payload = base64.urlsafe_b64decode(padded).decode()
        phone, expires_text = payload.split("|", 1)
        expected = hmac.new(_session_secret().encode(), payload.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected) or int(expires_text) < int(time.time()):
            return
        row = find_by_phone(sb, "customers", phone)
        if row:
            login_session(row)
            st.session_state["remember_me"] = True
    except Exception:
        return


def forget_customer_session():
    if cookie_controller:
        try:
            cookie_controller.remove("halago_customer_session")
        except Exception:
            pass


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
    """الدخول برقم الهاتف فقط — مرة واحدة، وتبقى الجلسة محفوظة على الجهاز."""
    st.markdown(
        """
        <div class="kg-auth-hero">
            <div class="kg-auth-logo">🛒</div>
            <div class="kg-auth-name">Halago</div>
            <div class="kg-auth-tag">هلا بك... اطلب براحة</div>
        </div>
        <div class="kg-auth-card">
            <div class="kg-auth-cardtitle">الدخول برقم الهاتف</div>
            <div class="kg-auth-sub">أدخل رقمك مرة واحدة فقط، وسنحفظ جلستك على هذا الجهاز.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form("phone_login_form"):
        phone = st.text_input("رقم الهاتف", placeholder="07XXXXXXXX")
        go = st.form_submit_button("متابعة", use_container_width=True)

    st.caption("بالدخول أنت توافق على استخدام رقمك لتوصيل طلباتك فقط.")

    if not go:
        return

    if not valid_phone(phone):
        st.error("أدخل رقم هاتف أردني صحيح مثل 0797123456.")
        return

    np_ = norm_phone(phone)
    try:
        row = find_by_phone(sb, "customers", np_)
        if not row:
            # إنشاء حساب جديد برقم الهاتف فقط (بدون PIN)
            try:
                sb.table("customers").insert({
                    "name": "", "phone": np_, "address": "",
                    "delivery_notes": "", "map_link": "", "email": "",
                }).execute()
            except Exception:
                sb.table("customers").insert({"phone": np_}).execute()
            row = find_by_phone(sb, "customers", np_)
        if not row:
            st.error("تعذر إنشاء الحساب، حاول مرة أخرى.")
            return
        login_session(row)
        st.session_state.remember_me = True
        remember_customer(np_)
        st.rerun()
    except Exception as e:
        st.error(f"تعذر تسجيل الدخول: {e}")


restore_customer_session()

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


def place_order(cart, payment, delivery, xy, via_whatsapp=False, discount=0.0, coupon_code=""):
    subtotal = cart_subtotal(cart)
    total = max(0.0, subtotal + delivery + SERVICE_FEE - float(discount or 0))
    summary = "\n".join(
        f"- {i['name']} ×{i.get('qty', 1)} ({safe_price(i['price']) * int(i.get('qty', 1)):.2f} د.أ) [المتجر: {i['merchant']}]"
        for i in cart)
    summary += f"\nالتوصيل: {delivery:.2f} د.أ"
    if discount > 0 and coupon_code:
        summary += f"\nكوبون الخصم: {coupon_code} (-{discount:.2f} د.أ)"
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
    st.markdown(
        "<div class='kg-cart-head'><div class='kg-cart-title'>🛍 السلة</div>"
        "<div class='kg-cart-count'>راجع أصنافك وأكمل طلبك</div></div>",
        unsafe_allow_html=True,
    )

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

        _hc1, _hc2 = st.columns([2, 1])
        with _hc1:
            _nitems = sum(int(_i.get("qty", 1)) for _i in st.session_state.cart)
            st.markdown(f"<div class='kg-cart-count'>{_nitems} صنف في سلتك</div>", unsafe_allow_html=True)
        with _hc2:
            if st.button("🗑 إفراغ السلة", key=f"clear_cart_{prefix}", use_container_width=True):
                st.session_state.cart = []
                st.session_state.coupon_code = ""
                st.rerun()

        for ci, item in enumerate(st.session_state.cart):
            q = int(item.get("qty", 1))
            st.markdown(
                f"<div class='kg-cart-item'><div class='kg-cart-item-name'>{html.escape(str(item['name']))}</div>"
                f"<div class='kg-cart-item-sub'>{html.escape(str(item['merchant']))} · "
                f"{safe_price(item['price']) * q:.2f} د.أ</div></div>",
                unsafe_allow_html=True,
            )
            q1, q2, q3 = st.columns([1, 1, 1])
            with q1:
                if st.button("➖", key=f"dec_{prefix}_{ci}", use_container_width=True):
                    if q > 1:
                        item["qty"] = q - 1
                    else:
                        st.session_state.cart.pop(ci)
                    st.rerun()
            with q2:
                st.markdown(f"<div class='kg-qty'>{q}</div>", unsafe_allow_html=True)
            with q3:
                if st.button("➕", key=f"inc_{prefix}_{ci}", use_container_width=True):
                    item["qty"] = q + 1
                    st.rerun()

        xy = customer_xy()
        delivery, uses_km = compute_delivery(st.session_state.cart, xy)
        coupon_input = st.text_input(
            "🎟️ لديك كوبون خصم؟",
            value=st.session_state.get("coupon_code", ""),
            key=f"coupon_input_{prefix}",
            placeholder="اكتب الكود مثل HALAGO10",
        )
        coupon_cols = st.columns([1, 1.5])
        with coupon_cols[0]:
            apply_coupon = st.button("تطبيق الكوبون", key=f"apply_coupon_{prefix}", use_container_width=True)
        with coupon_cols[1]:
            if st.session_state.get("coupon_code"):
                st.caption(f"الكوبون الحالي: `{st.session_state.coupon_code}`")
        if apply_coupon:
            discount_check, coupon_check = coupon_discount(coupon_input, subtotal)
            if coupon_check:
                st.session_state.coupon_code = coupon_input.strip().upper()
                st.success(f"تم تطبيق {coupon_check['label']} على قيمة الأصناف.")
                st.rerun()
            else:
                st.session_state.coupon_code = ""
                st.error("كود الكوبون غير صحيح أو لا ينطبق على السلة.")

        discount, active_coupon = coupon_discount(st.session_state.get("coupon_code", ""), subtotal)
        total = max(0.0, subtotal + delivery + SERVICE_FEE - discount)

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
        if discount > 0:
            st.write(f"🎟️ **الخصم ({st.session_state.coupon_code}):** -{discount:.2f} د.أ")
        st.markdown(f"### 💰 الإجمالي النهائي: {total:.2f} د.أ")
        if not xy:
            st.warning("رابط موقعك على خرائط جوجل غير محدد أو غير صالح (من صفحة حسابي)، لن يرى السائق موقعك على الخريطة.")

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
                        oid, wa = place_order(
                            st.session_state.cart, payment, delivery, xy, via_wa,
                            discount=discount, coupon_code=st.session_state.get("coupon_code", ""),
                        )
                        st.session_state.last_order = {"id": oid, "wa": wa}
                        st.session_state.cart = []
                        st.session_state.coupon_code = ""
                        st.rerun()
                    except Exception as e:
                        st.error(f"خطأ أثناء إرسال الطلب: {e}")

    st.markdown('</div>', unsafe_allow_html=True)


# ============================================================
# عناصر الشاشة الرئيسية (نمط طلبات)
# ============================================================
def _keyed_container(key):
    try:
        return st.container(key=key)
    except TypeError:
        return st.container()


def render_home_greeting():
    _cname = str(st.session_state.get("customer_name") or "").strip()
    _greet = "مساء الخير" if datetime.now().hour >= 12 else "صباح الخير"
    _line = f"{_greet} {_cname}" if _cname else _greet
    st.markdown(
        f"""
        <div class="kg-greet">
            <div class="kg-greet-title">{html.escape(_line)} ☀️</div>
            <div class="kg-greet-sub">ماذا ترغب اليوم؟</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_home_offers():
    st.markdown("<div class='kg-section-title'>🎁 عروض اليوم</div>", unsafe_allow_html=True)
    _offers = [
        ("o1", "خصم 10%", "على قيمة أصنافك باستخدام كود HALAGO10", "استخدم الكود"),
        ("o2", "توصيل سريع", "متاجر الكرك قريبة منك وجاهزة للتوصيل", "اطلب الآن"),
        ("o3", "كوبون ترحيبي", "خصم 1.00 د.أ على أول طلب بكود WELCOME", "جرّب الآن"),
    ]
    _cols = st.columns(3)
    for _oi, (_cls, _t, _s, _tag) in enumerate(_offers):
        with _cols[_oi % 3]:
            st.markdown(
                f"<div class='kg-offer-card {_cls}'>"
                f"<div class='kg-offer-title'>{_t}</div>"
                f"<div class='kg-offer-sub'>{_s}</div>"
                f"<div class='kg-offer-tag'>{_tag}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )


def render_store_card(store, key, search_text="", orders=None):
    """بطاقة متجر موحّدة: صورة + اسم + تقييم + وقت وتكلفة التوصيل + زر دخول."""
    sname = str(store.get("name") or "متجر")
    scat = str(store.get("category") or "").strip()
    sloc = str(store.get("location") or "").strip()
    eta = html.escape(merchant_eta(store))
    badge = html.escape(merchant_badge(store))
    fee_value = store.get("delivery_fee")
    fee_text = f"من {safe_price(fee_value):.2f} د.أ" if fee_value is not None else "حسب الموقع"
    try:
        rate = float(store.get("rating") or store.get("avg_rating") or 0)
    except Exception:
        rate = 0.0
    rate = max(0.0, min(5.0, rate))
    rate_html = (f"<span class='kg-pill kg-pill-rate'>★ {rate:.1f}</span>" if rate > 0
                 else "<span class='kg-pill kg-pill-new'>جديد</span>")
    hot_html = f"<span class='kg-pill kg-pill-hot'>🔥 {int(orders)} طلب</span>" if orders else ""
    sub = html.escape(" • ".join(x for x in (scat, sloc) if x))

    with _keyed_container(f"store_card_{key}"):
        c_img, c_info = st.columns([1, 2.3], gap="small")
        with c_img:
            display_image(store.get("image_data"), width=120, fallback="🏬")
        with c_info:
            st.markdown(
                f"<div class='kg-sc-name'>{html.escape(sname)}</div>"
                f"<div class='kg-sc-sub'>{sub}</div>"
                f"<div class='kg-sc-meta'>{rate_html}<span>⏱ {eta}</span><span>🚚 {fee_text}</span>{hot_html}</div>"
                f"<div class='kg-sc-badge'>✓ {badge}</div>",
                unsafe_allow_html=True,
            )
        if st.button("عرض المتجر", key=f"enter_store_{key}", use_container_width=True):
            st.session_state.selected_merchant = sname
            st.session_state.store_q = search_text or ""
            st.session_state.store_page = 0
            st.rerun()


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
st.markdown(
    f"<div class='kg-user-chip'>👤 {html.escape(str(st.session_state.customer_name or st.session_state.phone))}</div>",
    unsafe_allow_html=True,
)
st.markdown("<div class='kg-bottom-nav'></div>", unsafe_allow_html=True)
nav_cols = st.columns(3)
with nav_cols[0]:
    if st.button("🏠 الرئيسية", key="nav_home", use_container_width=True):
        st.session_state.nav_tab = "الرئيسية"
        st.session_state.selected_merchant = None
        st.session_state.search_query = ""
        st.session_state.search_input_key += 1
        st.rerun()
with nav_cols[1]:
    if st.button("📦 طلباتي", key="nav_orders", use_container_width=True):
        st.session_state.nav_tab = "الطلبات"
        st.session_state.selected_merchant = None
        st.rerun()
with nav_cols[2]:
    if st.button("👤 حسابي", key="nav_account", use_container_width=True):
        st.session_state.nav_tab = "الحساب"
        st.session_state.selected_merchant = None
        st.rerun()


# ============================================================
# 1. الرئيسية
# ============================================================
if st.session_state.nav_tab == "الرئيسية":

    st.markdown(
        f"""
        <div class="kg-header">
            <div class="kg-location">📍 التوصيل إلى <b>{html.escape(str(st.session_state.customer_address or 'عنوانك'))}</b>　⌄</div>
            <div class="kg-home-title">🛒 Halago</div>
            <div class="kg-home-sub">كل ما تحتاجه من متاجر الكرك في مكان واحد</div>
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
            st.session_state.search_query = ""
            st.session_state.selected_category = "الكل"
            st.session_state.search_input_key += 1
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
        render_home_greeting()

        user_input = st.text_input(
            "search",
            value=st.session_state.search_query,
            key=f"user_search_box_{st.session_state.search_input_key}",
            placeholder="🔍 ابحث عن مطعم أو متجر أو صنف ثم اضغط Enter",
            label_visibility="collapsed",
        )

        current_search = user_input.strip()
        if current_search != st.session_state.search_query:
            st.session_state.search_query = current_search

        if current_search:
            if st.button("✕ مسح البحث والعودة للأقسام", key="clear_search_btn"):
                st.session_state.search_query = ""
                st.session_state.search_input_key += 1
                st.rerun()
        else:
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
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                        # اسم القسم فقط (بدون أي مربع أو إطار)
                        btn_label = c_name
                        if st.button(btn_label, key=(f"cat_card_sel_{i+j}" if is_sel else f"cat_card_{i+j}"), use_container_width=False):
                            st.session_state.selected_category = c_name
                            st.query_params["cat"] = c_name
                            st.session_state.search_query = ""
                            st.session_state.search_input_key += 1
                            st.rerun()

            render_home_offers()

            popular = load_popular_merchants()
            if popular:
                st.markdown("<div class='kg-section-title'>🔥 الأكثر طلبًا</div>", unsafe_allow_html=True)
                popular_cols = st.columns(min(3, len(popular)))
                for pi, (popular_store, order_count) in enumerate(popular):
                    with popular_cols[pi % len(popular_cols)]:
                        render_store_card(popular_store, f"pop_{pi}", "", orders=order_count)

        left, right = st.columns([2.2, 1], gap="large")

        with left:
            if st.session_state.selected_category == "الكل" or current_search:
                filtered_merchants = all_merchants
            else:
                selected_cat = st.session_state.selected_category.strip()
                filtered_merchants = [
                    m for m in all_merchants
                    if str(m.get("category", "")).strip() == selected_cat
                ]

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

            _cat_now = st.session_state.selected_category
            _cat_txt = (f" — نتائج «{html.escape(current_search)}»" if current_search else ("" if _cat_now == "الكل" else f" — {html.escape(str(_cat_now))}"))
            st.markdown(
                f"<div class='kg-section-title'>المتاجر القريبة منك{_cat_txt}"
                f"<span class='kg-section-count'>({len(merchants)})</span></div>",
                unsafe_allow_html=True,
            )

            if not merchants:
                st.info("لا توجد متاجر مطابقة للبحث أو مضافة حالياً في هذا القسم.")

            store_cols_count = 2
            for mi in range(0, len(merchants), store_cols_count):
                row_stores = merchants[mi:mi + store_cols_count]
                s_cols = st.columns(len(row_stores))
                for sj, store in enumerate(row_stores):
                    with s_cols[sj]:
                        render_store_card(store, f"m_{mi + sj}", current_search)

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

    st.markdown("### 📍 حدّد موقع التسليم على الخريطة")
    st.caption("اضغط على مكان منزلك في الخريطة ثم اضغط «حفظ الموقع المحدد». لا تحتاج إلى كتابة الإحداثيات.")
    render_customer_location_picker()

    with st.form("account_form"):
        a_name = st.text_input("اسمك الكريم:", value=st.session_state.customer_name)
        a_email = st.text_input("البريد الإلكتروني (اختياري):", value=st.session_state.customer_email)
        a_addr = st.text_area("عنوان التوصيل (المنطقة، الشارع، أقرب معلم):", value=st.session_state.customer_address)
        a_notes = st.text_area("ملاحظات خاصة لمندوب التوصيل:", value=st.session_state.delivery_notes)
        st.markdown("📍 **الموقع الجغرافي:**")
        a_link = st.text_input("رابط الموقع (يُملأ تلقائيًا بعد اختيار الخريطة):", value=st.session_state.customer_map_link)
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

    col_b1, col_b2 = st.columns(2)
    with col_b1:
        if st.button("🚪 تسجيل الخروج", use_container_width=True):
            forget_customer_session()
            for k in ("logged_in", "customer_id", "phone", "customer_name", "customer_email", "customer_address",
                      "delivery_notes", "customer_map_link", "cart", "last_order"):
                st.session_state.pop(k, None)
            st.session_state.nav_tab = "الرئيسية"
            st.rerun()
    with col_b2:
        with st.expander("🗑 حذف حسابي نهائيًا"):
            confirm = st.text_input("اكتب كلمة «حذف» لتأكيد الحذف", key="del_confirm")
            if st.button("حذف الحساب نهائيًا", use_container_width=True):
                if confirm.strip() != "حذف":
                    st.error("اكتب كلمة «حذف» للتأكيد.")
                else:
                    row = find_by_phone(sb, "customers", st.session_state.phone)
                    if row:
                        sb.table("customers").delete().eq("id", row["id"]).execute()
                    for k in ("logged_in", "customer_id", "phone", "customer_name", "customer_email", "customer_address",
                              "delivery_notes", "customer_map_link", "cart", "last_order"):
                        st.session_state.pop(k, None)
                    st.rerun()
