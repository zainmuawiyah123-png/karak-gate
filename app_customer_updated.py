import sys
import io
import base64
from datetime import datetime
import urllib.parse

import streamlit as st
from supabase import create_client


# ============================================================
# إعداد UTF-8
# ============================================================
try:
    sys.stdout = io.TextIOWrapper(
        sys.stdout.buffer,
        encoding="utf-8"
    )
    sys.stderr = io.TextIOWrapper(
        sys.stderr.buffer,
        encoding="utf-8"
    )
except Exception:
    pass


# ============================================================
# إعداد Supabase
# ============================================================
SUPABASE_URL = "https://tzkdxodvlzggmcntnqer.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InR6a2R4b2R2bHpnZ21jbnRucWVyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTA5MzM3MzksImV4cCI6MjEwNjUwOTczOX0.M944yHglTXVyPrxySSQj0MBaqpr2I_8ub7Uoofbd2_4"

try:
    if "SUPABASE_ANON_KEY" in st.secrets:
        SUPABASE_ANON_KEY = str(
            st.secrets["SUPABASE_ANON_KEY"]
        ).strip()
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
    background: #F8F9FA !important;
    color: #2D3142 !important;
}
.block-container {
    padding-top: 0.8rem !important;
    padding-bottom: 3rem !important;
    max-width: 1400px !important;
}
h1, h2, h3, h4, h5, h6, p, label, span {
    color: #2D3142 !important;
}
div[data-testid="column"] .stButton > button {
    background: #FF5722 !important;
    color: #FFFFFF !important;
    border-radius: 4px !important;
    border: 0 !important;
    font-weight: bold !important;
    font-size: 10px !important;
    padding: 1px 2px !important;
    min-height: 22px !important;
    max-width: 75px !important;
    margin: 0 auto !important;
    display: block !important;
}
.kg-header {
    background: linear-gradient(135deg, #E64A19, #FF7043);
    border-radius: 10px;
    padding: 10px 14px;
    margin-bottom: 12px;
    box-shadow: 0 3px 10px rgba(0,0,0,0.06);
}
.kg-header-title {
    color: white !important;
    font-size: 18px;
    font-weight: 800;
    margin: 0;
}
.kg-header-sub {
    color: white !important;
    font-size: 11px;
    margin: 0;
}
.kg-store {
    background: white;
    border-radius: 18px;
    padding: 15px;
    margin-bottom: 18px;
    border: 1px solid #E6E6E6;
    box-shadow: 0 4px 16px rgba(0,0,0,0.06);
}
.kg-store-title {
    font-size: 20px;
    font-weight: 900;
    margin-bottom: 5px;
}
.kg-cart {
    background: white;
    border-radius: 18px;
    padding: 18px;
    border: 1px solid #E5E5E5;
    box-shadow: 0 4px 16px rgba(0,0,0,0.06);
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
        return create_client(
            SUPABASE_URL.strip(),
            SUPABASE_ANON_KEY.strip()
        )
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
    st.session_state.phone = "0790000000"

if "customer_name" not in st.session_state:
    st.session_state.customer_name = "أبو عدي"

if "customer_address" not in st.session_state:
    st.session_state.customer_address = "الكرك - المرج"

if "cart" not in st.session_state:
    st.session_state.cart = []

if "nav_tab" not in st.session_state:
    st.session_state.nav_tab = "الرئيسية"

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
    {"name": "الكل", "image": "https://images.unsplash.com/photo-1504674900247-0877df9cc836?auto=format&fit=crop&w=200&q=80"},
    {"name": "مطاعم", "image": "https://images.unsplash.com/photo-1515003197210-e0cd71810b5f?auto=format&fit=crop&w=200&q=80"},
    {"name": "حلويات", "image": "https://images.unsplash.com/photo-1578985545062-69928b1d9587?auto=format&fit=crop&w=200&q=80"},
    {"name": "ماركت", "image": "https://images.unsplash.com/photo-1542838132-92c53300491e?auto=format&fit=crop&w=200&q=80"},
    {"name": "محامص ومكسرات", "image": "https://images.unsplash.com/photo-1599599810769-bcde5a160d32?auto=format&fit=crop&w=200&q=80"},
    {"name": "خضروات وفواكه", "image": "https://images.unsplash.com/photo-1619566636858-adf3ef46400b?auto=format&fit=crop&w=200&q=80"},
    {"name": "لحوم", "image": "https://images.unsplash.com/photo-1603048297172-c92544798d5a?auto=format&fit=crop&w=200&q=80"},
    {"name": "صيدليات ومستلزمات طبيه", "image": "https://images.unsplash.com/photo-1585435557343-3b092031a831?auto=format&fit=crop&w=200&q=80"}
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
    if st.button("📦 طلباتي", use_container_width=True):
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

    search = st.text_input("🔍 ابحث عن متجر أو صنف في الكرك...", "")

    st.subheader("📁 الأقسام الرئيسية")
    
    cols = st.columns(4)
    for i, cat in enumerate(categories):
        c_name = cat["name"]
        c_img = cat["image"]
        is_sel = (st.session_state.selected_category == c_name)
        border_style = "border: 2px solid #2D3142; background: #FFFFFF;" if is_sel else "border: 1px solid #E5E5E5; background: #FFFFFF;"
        
        with cols[i % 4]:
            st.markdown(
                f"""
                <div style="{border_style} width: 75px; height: 75px; border-radius: 8px; padding: 4px; text-align: center; margin: 0 auto 4px auto; display: flex; flex-direction: column; justify-content: center; align-items: center;">
                    <img src="{c_img}" style="width: 28px; height: 28px; object-fit: cover; border-radius: 50%; margin-bottom: 2px; display: block;">
                    <div style="font-weight: 750; font-size: 10px; color: #2D3142; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 68px;">{c_name}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
            if st.button(f"اختر", key=f"cat_card_{i}", use_container_width=True):
                st.session_state.selected_category = c_name
                st.query_params["cat"] = c_name
                st.rerun()

    st.write(f"**القسم الحالي المحدد:** `{st.session_state.selected_category}`")

    left, right = st.columns([2.2, 1], gap="large")

    with left:
        st.subheader("🏬 المتاجر المعتمدة والأصناف")

        try:
            q = sb.table("merchants").select("*")
            if st.session_state.selected_category != "الكل":
                q = q.eq("category", st.session_state.selected_category)
            merchants = q.execute().data or []
        except Exception:
            merchants = []

        if search:
            s = search.lower().strip()
            merchants = [m for m in merchants if s in str(m.get("name") or "").lower() or s in str(m.get("category") or "").lower()]

        if not merchants:
            st.info("لا توجد متاجر مضافة حالياً في هذا القسم.")

        for mi, m in enumerate(merchants):
            mname = m.get("name", "متجر")
            mlink = m.get("map_link", "")
            
            st.markdown('<div class="kg-store">', unsafe_allow_html=True)
            
            col_img, col_info = st.columns([1, 4])
            with col_img:
                display_image(m.get("image_data"), width=50, fallback="🏬")
            with col_info:
                st.markdown(f'<div class="kg-store-title">🏬 {mname}</div>', unsafe_allow_html=True)
                st.caption(f"التصنيف: **{m.get('category','')}** | الموقع: {m.get('location','')}")
                
                if mlink:
                    st.markdown(f'<a href="{mlink}" target="_blank">🗺 فتح موقع المتجر على خرائط جوجل</a>', unsafe_allow_html=True)

            try:
                products = sb.table("products").select("*").eq("merchant_name", mname).execute().data or []
            except Exception:
                products = []

            if products:
                st.write("📋 **الأصناف المتوفرة:**")
                for p in products:
                    item_name = p.get("item_name", "صنف")
                    quantity = p.get("quantity", "")
                    unit = p.get("unit", "")
                    price = safe_price(p.get("price"))

                    p_col1, p_col2, p_col3 = st.columns([1, 4, 2])
                    
                    with p_col1:
                        display_image(p.get("image_path"), width=40, fallback="🍽️")
                    
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
                st.info("لا توجد أصناف مضافة حالياً من هذا المتجر.")

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
                        "customer_address": st.session_state.customer_address,
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
# 2. الطلبات
# ============================================================
elif st.session_state.nav_tab == "الطلبات":
    st.markdown(
        """
        <div class="kg-header">
            <div class="kg-header-title">📦 طلباتي</div>
            <div class="kg-header-sub">متابعة حالة طلباتك السابقة والنشطة</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    try:
        orders = sb.table("orders").select("id,order_status,driver_name,total_amount,created_at,order_details").eq("customer_phone", st.session_state.phone).order("id", desc=True).execute().data or []
        if orders:
            for ord_item in orders:
                st.markdown(f"""
                <div style="background:white; border-radius:12px; padding:15px; margin-bottom:10px; border:1px solid #ddd;">
                    <b>رقم الطلب: #{ord_item.get('id')}</b><br>
                    <span>الحالة: <b>{ord_item.get('order_status')}</b></span><br>
                    <span>المبلغ: {ord_item.get('total_amount')} د.أ</span><br>
                    <pre style="background:#f9f9f9; padding:8px; border-radius:6px;">{ord_item.get('order_details')}</pre>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("لا توجد طلبات سابقة.")
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
            <div class="kg-header-sub">قم بتحديث معلوماتك وتحديد موقعك لتسهيل عملية التوصيل</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.session_state.customer_name = st.text_input("اسمك الكريم:", st.session_state.customer_name)
    st.session_state.phone = st.text_input("رقم الهاتف:", st.session_state.phone)
    st.session_state.customer_address = st.text_area("تفاصيل العنوان (المنطقة، الشارع، رقم البناية):", st.session_state.customer_address)

    if st.button("💾 حفظ التعديلات", use_container_width=True):
        try:
            sb.table("customers").upsert(
                {
                    "name": st.session_state.customer_name,
                    "phone": st.session_state.phone,
                    "address": st.session_state.customer_address
                },
                on_conflict="phone"
            ).execute()
            st.success("🎉 تم حفظ وتحديث بياناتك بنجاح!")
            st.rerun()
        except Exception as e:
            st.error(f"خطأ أثناء حفظ البيانات: {e}")
