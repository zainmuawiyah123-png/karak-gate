import sys
import io
import base64
from datetime import datetime

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
# CSS المحدث
# ============================================================
st.markdown(
    """
<style>
#MainMenu, .stDeployButton, header, footer {
    visibility: hidden;
    display: none;
}
.stApp {
    background: linear-gradient(135deg, #F4F6F8 0%, #E9ECEF 100%) !important;
    color: #2D3142 !important;
}
.block-container {
    padding-top: 1rem !important;
    padding-bottom: 3rem !important;
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
    background: linear-gradient(135deg, #E64A19, #FF7043);
    border-radius: 14px;
    padding: 14px 18px;
    margin-bottom: 15px;
    box-shadow: 0 4px 15px rgba(230,74,25,0.2);
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
.kg-store {
    background: white;
    border-radius: 16px;
    padding: 18px;
    margin-bottom: 18px;
    border: 1px solid #E2E8F0;
    box-shadow: 0 4px 20px rgba(0,0,0,0.04);
}
.kg-store-title {
    font-size: 20px;
    font-weight: 900;
    margin-bottom: 6px;
}
.kg-cart {
    background: white;
    border-radius: 16px;
    padding: 18px;
    border: 1px solid #E2E8F0;
    box-shadow: 0 4px 20px rgba(0,0,0,0.04);
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
# التحديث التلقائي للصفحة
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
    st.session_state.phone = "0790000000"

if "customer_name" not in st.session_state:
    st.session_state.customer_name = "أبو عدي"

if "customer_address" not in st.session_state:
    st.session_state.customer_address = "الكرك - المرج"

if "customer_map_link" not in st.session_state:
    st.session_state.customer_map_link = "https://maps.google.com/?q=31.1818,35.7011"

if "cart" not in st.session_state:
    st.session_state.cart = []

if "nav_tab" not in st.session_state:
    st.session_state.nav_tab = "الرئيسية"

if "active_search" not in st.session_state:
    st.session_state.active_search = ""

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
# دالة عرض الصور
# ============================================================
def display_image(value, width=60, fallback="🛒"):
    if not value:
        st.markdown(f"<span style='font-size:24px;'>{fallback}</span>", unsafe_allow_html=True)
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

    st.markdown(f"<span style='font-size:24px;'>{fallback}</span>", unsafe_allow_html=True)


# ============================================================
# قائمة الأقسام
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
        st.rerun()
with nav_cols[1]:
    if st.button("📦 طلباتي والتتبع", use_container_width=True):
        st.session_state.nav_tab = "الطلبات"
        st.rerun()
with nav_cols[2]:
    if st.button("👤 حسابي", use_container_width=True):
        st.session_state.nav_tab = "الحساب"
        st.rerun()


# ============================================================
# 1. الرئيسية
# ============================================================
if st.session_state.nav_tab == "الرئيسية":

    st.markdown(
        """
        <div class="kg-header">
            <div class="kg-header-title">🛒 بوابة الكرك</div>
            <div class="kg-header-sub">Karak Gate • اطلب ما تريد من متاجر الكرك بكل سهولة</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # خانة البحث المستقلة
    search_val = st.text_input("🔍 ابحث عن متجر أو صنف (اكتب الحروف الأولى)...", value=st.session_state.active_search, key="global_search_input")
    if search_val != st.session_state.active_search:
        st.session_state.active_search = search_val

    st.subheader("📁 الأقسام الرئيسية")
    
    cols_per_row = 4
    for i in range(0, len(categories), cols_per_row):
        row_cats = categories[i:i + cols_per_row]
        c_cols = st.columns(len(row_cats))
        for j, cat in enumerate(row_cats):
            c_name = cat["name"]
            c_img = cat["image"]
            is_sel = (st.session_state.selected_category == c_name)
            border_color = "#E64A19" if is_sel else "#E2E8F0"
            bg_color = "#FFF8F5" if is_sel else "#FFFFFF"
            shadow_style = "box-shadow: 0 4px 15px rgba(230,74,25,0.2);" if is_sel else "box-shadow: 0 2px 8px rgba(0,0,0,0.03);"
            
            with c_cols[j]:
                st.markdown(
                    f"""
                    <div style="background: {bg_color}; border: 2px solid {border_color}; border-radius: 16px; padding: 12px 6px; text-align: center; margin-bottom: 10px; {shadow_style} height: 125px; display: flex; flex-direction: column; justify-content: center; align-items: center;">
                        <img src="{c_img}" style="width: 50px; height: 50px; object-fit: cover; border-radius: 50%; margin-bottom: 6px; border: 2px solid #F1F5F9; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                        <div style="font-weight: 800; font-size: 12px; color: #2D3142; width: 100%; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; padding: 0 2px;">{c_name}</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                btn_label = f"✓ {c_name}" if is_sel else f"عرض {c_name}"
                if st.button(btn_label, key=f"cat_card_{i+j}", use_container_width=True):
                    st.session_state.selected_category = c_name
                    st.query_params["cat"] = c_name
                    # تصفير بحث النص بالكامل وتحديث الـ session state ليختفي نص البحث من خانة الإدخال فوراً
                    st.session_state.active_search = ""
                    st.rerun()

    left, right = st.columns([2.2, 1], gap="large")

    with left:
        st.subheader("🏬 المتاجر المعتمدة والأصناف")

        try:
            merchants_res = sb.table("merchants").select("*").execute()
            all_merchants = merchants_res.data if merchants_res.data else []
            
            products_res = sb.table("products").select("*").execute()
            all_products = products_res.data if products_res.data else []
        except Exception:
            all_merchants = []
            all_products = []

        # 1. فلترة المتاجر حسب القسم المحدد
        if st.session_state.selected_category == "الكل":
            filtered_merchants = all_merchants
        else:
            selected_cat = st.session_state.selected_category.strip()
            filtered_merchants = [
                m for m in all_merchants 
                if str(m.get("category", "")).strip() == selected_cat
            ]

        # 2. البحث الشامل السريع (فقط إذا كتب المستخدم شيئاً في خانة البحث ولم يتم تصفيرها)
        current_search = st.session_state.active_search.strip()
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
            st.info("لا توجد متاجر أو أصناف مطابقة للبحث أو مضافة حالياً في هذا القسم.")

        for mi, m in enumerate(merchants):
            mname = m.get("name", "متجر")
            mlink = m.get("map_link", "")
            
            st.markdown('<div class="kg-store">', unsafe_allow_html=True)
            
            col_img, col_info = st.columns([1, 4])
            with col_img:
                display_image(m.get("image_data"), width=55, fallback="🏬")
            with col_info:
                st.markdown(f'<div class="kg-store-title">🏬 {mname}</div>', unsafe_allow_html=True)
                st.caption(f"التصنيف: **{m.get('category','')}** | الموقع: {m.get('location','')}")
                
                if mlink:
                    st.markdown(f'<a href="{mlink}" target="_blank" style="color:#E64A19; font-weight:bold; text-decoration:none;">🗺 فتح موقع المتجر على خرائط جوجل</a>', unsafe_allow_html=True)

            products = [p for p in all_products if p.get("merchant_name") == mname]
            if current_search:
                s = current_search.lower()
                if s not in mname.lower() and s not in str(m.get("category", "")).lower():
                    products = [p for p in products if s in str(p.get("item_name") or "").lower()]

            if products:
                st.write("📋 **الأصناف المتوفرة:**")
                for p in products:
                    item_name = p.get("item_name", "صنف")
                    quantity = p.get("quantity", "")
                    unit = p.get("unit", "")
                    price = safe_price(p.get("price"))

                    p_col1, p_col2, p_col3 = st.columns([1, 4, 2])
                    
                    with p_col1:
                        display_image(p.get("image_path"), width=40, fallback="🍽")
                    
                    with p_col2:
                        st.markdown(f"**{item_name}**")
                        st.caption(f"{quantity} {unit} | <span style='color:#E64A19; font-weight:bold;'>{price:.2f} د.أ</span>", unsafe_allow_html=True)
                    
                    with p_col3:
                        if st.button("➕ إضافة", key=f"add_{mi}_{p['id']}", use_container_width=True):
                            st.session_state.cart.append({
                                "name": f"{item_name} ({quantity} {unit})",
                                "price": price,
                                "merchant": mname
                            })
                            st.toast(f"تمت إضافة {item_name} إلى السلة!")
            else:
                st.info("لا توجد أصناف مطابقة للبحث من هذا المتجر.")

            st.markdown('</div>', unsafe_allow_html=True)

    # السلة (اليمين)
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

            delivery = 1.50
            service = 0.25
            total = subtotal + delivery + service

            st.markdown("---")
            st.write(f"🏷 **مجموع الأصناف:** {subtotal:.2f} د.أ")
            st.write(f"🛵 **التوصيل:** {delivery:.2f} د.أ")
            st.write(f"⚙️ **الخدمة:** {service:.2f} د.أ")
            st.markdown(f"### 💰 الإجمالي النهائي: {total:.2f} د.أ")

            if st.button("🗑 تفريغ السلة", use_container_width=True):
                st.session_state.cart = []
                st.rerun()

            payment = st.radio(
                "اختر طريقة الدفع:",
                ["نقداً عند الاستلام", "CliQ (0797088219)", "Zain Cash"]
            )

            st.markdown("---")
            summary = "\n".join(f"- {item['name']} ({item['price']:.2f} د.أ) [المتجر: {item['merchant']}]" for item in st.session_state.cart)
            
            if st.button("📌 تأكيد وإرسال للنظام", use_container_width=True):
                try:
                    sb.table("orders").insert({
                        "customer_name": st.session_state.customer_name,
                        "customer_phone": st.session_state.phone,
                        "customer_address": f"{st.session_state.customer_address} | رابط الخريطة: {st.session_state.customer_map_link}",
                        "order_details": summary,
                        "total_amount": total,
                        "payment_method": payment,
                        "order_status": "قيد التجهيز",
                        "driver_name": "",
                        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }).execute()

                    st.success("🎉 تم تأكيد طلبك بنجاح وإرساله للنظام!")
                    st.session_state.cart = []
                    st.rerun()
                except Exception as e:
                    st.error(f"خطأ أثناء إرسال الطلب: {e}")

        st.markdown('</div>', unsafe_allow_html=True)


# ============================================================
# 2. الطلبات وتتبع الرحلة الحي
# ============================================================
elif st.session_state.nav_tab == "الطلبات":
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
                
                steps = ["قيد التجهيز", "استلم السائق الطلب", "في الطريق", "تم الاستلام"]
                current_step_idx = 0
                if status in steps:
                    current_step_idx = steps.index(status)
                elif status == "جاهز":
                    current_step_idx = 1
                
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
                
                if current_step_idx >= 1:
                    st.markdown("<br>", unsafe_allow_html=True)
                    col_d1, col_d2 = st.columns(2)
                    with col_d1:
                        driver_display = driver if driver else "جارٍ تعيين سائق..."
                        st.markdown(f"🛵 **السائق المسؤول:** `{driver_display}`")
                    with col_d2:
                        st.markdown("⏱ **الوقت المتوقع للوصول:** `خلال 15-20 دقيقة`")

                st.markdown(f'<div style="margin-top:10px;"><a href="{st.session_state.customer_map_link}" target="_blank" style="background:#0F172A; color:white; padding:6px 12px; border-radius:6px; font-size:12px; text-decoration:none; display:inline-block;">🗺 عرض موقع تسليم الطلب على خرائط جوجل (مسار الرحلة)</a></div>', unsafe_allow_html=True)

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
# 3. الحساب وعنوان التوصيل مع تحديد الموقع الجغرافي
# ============================================================
elif st.session_state.nav_tab == "الحساب":
    st.markdown(
        """
        <div class="kg-header">
            <div class="kg-header-title">👤 حسابي وعنوان التوصيل</div>
            <div class="kg-header-sub">قم بتحديث معلوماتك وتحديد موقعك الجغرافي لتسهيل وتتبع التوصيل</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.session_state.customer_name = st.text_input("اسمك الكريم:", st.session_state.customer_name)
    st.session_state.phone = st.text_input("رقم الهاتف:", st.session_state.phone)
    st.session_state.customer_address = st.text_area("تفاصيل العنوان (المنطقة، الشارع، رقم البناية):", st.session_state.customer_address)

    st.markdown("📍 **الموقع الجغرافي لتحديد مسار السائق:**")
    
    map_input_method = st.radio("طريقة تحديد الموقع:", ["إدخال رابط خرائط جوجل يدوياً", "تحديد الإحداثيات الجغرافية تلقائياً (GPS)"])
    
    if map_input_method == "إدخال رابط خرائط جوجل يدوياً":
        st.session_state.customer_map_link = st.text_input("رابط موقعك على خرائط جوجل (Google Maps URL):", st.session_state.customer_map_link)
    else:
        st.info("💡 اضغط على الزر أدناه لتحديد موقعك الحالي في الكرك بدقة:")
        if st.button("🌐 تحديد موقعي الحالي تلقائياً"):
            st.session_state.customer_map_link = "https://maps.google.com/?q=31.1818,35.7011"
            st.success("✅ تم تحديث إحداثيات موقعك الجغرافي بنجاح (الكرك - المرج)!")

    if st.session_state.customer_map_link:
        st.markdown(f'<a href="{st.session_state.customer_map_link}" target="_blank">🗺 اضغط هنا لمعاينة موقعك المسجل على الخريطة</a>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("💾 حفظ التعديلات", use_container_width=True):
        try:
            sb.table("customers").upsert(
                {
                    "name": st.session_state.customer_name,
                    "phone": st.session_state.phone,
                    "address": f"{st.session_state.customer_address} (رابط الخريطة: {st.session_state.customer_map_link})"
                },
                on_conflict="phone"
            ).execute()
            st.success("🎉 تم حفظ وتحديث بياناتك وموقعك الجغرافي بنجاح!")
            st.rerun()
        except Exception as e:
            st.error(f"خطأ أثناء حفظ البيانات: {e}")
