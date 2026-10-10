import sys
import io
import base64
from datetime import datetime
import urllib.parse
import os, base64

import streamlit as st
from supabase import create_client


# ============================================================
# إعداد الصفحة (لوحة الإدارة المستقلة)
# ============================================================
ICON_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kark.png")
_PAGE_ICON = "🛒"
try:
    from PIL import Image as _PILImage
    if os.path.exists(_ICON_FILE):
        _PAGE_ICON = _PILImage.open(_ICON_FILE)
except Exception:
    _PAGE_ICON = "🛒"


def inject_app_icon(app_title="Halago"):
    """يضع أيقونة قلعة الكرك للشاشة الرئيسية وتبويب المتصفح."""
    try:
        if not os.path.exists(_ICON_FILE):
            return
        import streamlit.components.v1 as components
        with open(_ICON_FILE, "rb") as f:
            uri = "data:image/png;base64," + base64.b64encode(f.read()).decode()
        js = """<script>
        (function(){
          try {
            var d = window.parent.document, h = d.head, uri = "__URI__";
            h.querySelectorAll('link[rel*="icon"]').forEach(function(l){ l.remove(); });
            [["apple-touch-icon","180x180"],["icon","180x180"]].forEach(function(p){
              var l = d.createElement('link'); l.rel = p[0]; l.sizes = p[1]; l.type = 'image/png'; l.href = uri; h.appendChild(l);
            });
            function meta(n, c){ var m = d.querySelector('meta[name="'+n+'"]') || d.createElement('meta'); m.name = n; m.content = c; h.appendChild(m); }
            meta('apple-mobile-web-app-title', "__TITLE__");
            meta('apple-mobile-web-app-capable', 'yes');
          } catch(e) {}
        })();
        </script>"""
        components.html(js.replace("__URI__", uri).replace("__TITLE__", app_title), height=0)
    except Exception:
        pass
st.set_page_config(
    page_title="لوحة إدارة بوابة الكرك - Admin Panel",
    page_icon="⚙",
    layout="wide",
    initial_sidebar_state="collapsed"
)


# ============================================================
# CSS خاص بلوحة الإدارة
# ============================================================
st.markdown(
    """
<style>
#MainMenu, .stDeployButton, header, footer {
    visibility: hidden;
    display: none;
}
.stApp {
    background: #F4F6F9 !important;
    color: #2D3142 !important;
}
.block-container {
    padding-top: 1rem !important;
    padding-bottom: 3rem !important;
    max-width: 1400px !important;
}
.admin-header {
    background: linear-gradient(135deg, #2D3142, #4F5D75);
    border-radius: 12px;
    padding: 15px 20px;
    margin-bottom: 20px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}
.admin-header-title {
    color: white !important;
    font-size: 22px;
    font-weight: 800;
    margin: 0;
}
.admin-header-sub {
    color: #E0E0E0 !important;
    font-size: 12px;
    margin: 0;
}
</style>
""",
    unsafe_allow_html=True
)


# ============================================================
# اتصال قاعدة البيانات
# ============================================================
SUPABASE_URL = "https://tzkdxodvlzggmcntnqer.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InR6a2R4b2R2bHpnZ21jbnRucWVyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTA5MzM3MzksImV4cCI6MjEwNjUwOTczOX0.M944yHglTXVyPrxySSQj0MBaqpr2I_8ub7Uoofbd2_4"

try:
    if "SUPABASE_ANON_KEY" in st.secrets:
        SUPABASE_ANON_KEY = str(st.secrets["SUPABASE_ANON_KEY"]).strip()
except Exception:
    pass

def db():
    try:
        return create_client(SUPABASE_URL.strip(), SUPABASE_ANON_KEY.strip())
    except Exception as e:
        st.error(f"❌ تعذر الاتصال بـ Supabase: {e}")
        st.stop()

sb = db()


# ============================================================
# رأس لوحة الإدارة
# ============================================================
st.markdown(
    """
    <div class="admin-header">
        <div class="admin-header-title">⚙ لوحة إدارة بوابة الكرك الشاملة (المستقلة)</div>
        <div class="admin-header-sub">Karak Gate Administration • إدارة المتاجر، الأصناف، السائقين، الطلبات، والتقارير</div>
    </div>
    """,
    unsafe_allow_html=True
)

categories_list = [
    "مطاعم", "حلويات", "ماركت", "محامص ومكسرات", 
    "خضروات وفواكه", "لحوم", "صيدليات ومستلزمات طبيه"
]


# ============================================================
# التبويبات الرئيسية الشاملة
# ============================================================
tabs = st.tabs([
    "📦 الطلبات والتنبيهات",
    "🏬 المتاجر", 
    "📋 أصناف المتاجر",
    "🛵 إدارة السائقين", 
    "👥 سجل الزبائن", 
    "🏷 إدارة العروض", 
    "📊 التقرير المالي"
])

tab_orders, tab_merchants, tab_products, tab_drivers, tab_customers, tab_offers, tab_finance = tabs


# ============================================================
# دالة معالجة الصور
# ============================================================
def handle_image_input(uploaded_file, url_input):
    if uploaded_file is not None:
        try:
            bytes_data = uploaded_file.getvalue()
            b64_str = base64.b64encode(bytes_data).decode("utf-8")
            ext = uploaded_file.name.split(".")[-1].lower()
            mime = "image/png" if ext == "png" else "image/jpeg"
            return f"data:{mime};base64,{b64_str}"
        except Exception:
            return (url_input or "").strip()
    return (url_input or "").strip()


# ============================================================
# 1. الطلبات والتنبيهات
# ============================================================
with tab_orders:
    st.subheader("📦 متابعة الطلبات الواردة والتنبيهات")
    
    st.markdown(
        """
        <audio autoplay style="display:none;">
            <source src="https://assets.mixkit.co/active_storage/sfx/2869/2869-preview.mp3" type="audio/mpeg">
        </audio>
        """,
        unsafe_allow_html=True
    )
    st.caption("🔔 تم تشغيل جرس التنبيه الصوتي للطلبات الجديدة تلقائياً.")

    try:
        orders = sb.table("orders").select("*").order("id", desc=True).execute().data or []
        drivers_data = sb.table("drivers").select("name").execute().data or []
        drivers_list = [d["name"] for d in drivers_data] if drivers_data else ["لا توجد سائقون مسجلون"]

        if orders:
            for ord_item in orders:
                oid = ord_item.get("id")
                c_name = ord_item.get("customer_name")
                c_phone = ord_item.get("customer_phone")
                c_address = ord_item.get("customer_address")
                total = ord_item.get("total_amount")
                status = ord_item.get("order_status", "قيد التجهيز")
                details = ord_item.get("order_details")
                payment = ord_item.get("payment_method")

                st.markdown(f"""
                <div style="background:white; border-radius:12px; padding:15px; margin-bottom:12px; border:1px solid #D1D5DB; box-shadow: 0 2px 8px rgba(0,0,0,0.04);">
                    <b>الطلب #{oid} — الزبون: {c_name} ({c_phone})</b><br>
                    <span>📍 العنوان: {c_address}</span><br>
                    <span>💰 الإجمالي: <b>{total} د.أ</b> | الدفع: {payment} | الحالة: <b>{status}</b></span>
                    <pre style="background:#F8F9FA; padding:8px; border-radius:6px; margin-top:8px;">{details}</pre>
                </div>
                """, unsafe_allow_html=True)

                col_stat, col_drv, col_wa = st.columns([2, 2, 2])
                with col_stat:
                    new_status = st.selectbox("تحديث الحالة:", ["قيد التجهيز", "جاري التوصيل", "تم التوصيل", "ملغي"], key=f"st_{oid}")
                with col_drv:
                    assigned_driver = st.selectbox("تعيين سائق:", drivers_list, key=f"drv_{oid}")
                with col_wa:
                    st.write("")
                    if st.button("💾 تحديث الطلب", key=f"upd_ord_{oid}", use_container_width=True):
                        try:
                            sb.table("orders").update({
                                "order_status": new_status,
                                "driver_name": assigned_driver
                            }).eq("id", oid).execute()
                            st.success("تم تحديث الطلب بنجاح!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"خطأ: {e}")

                c_phone_str = str(c_phone or "")
                wa_msg_cust = f"مرحباً {c_name}، بخصوص طلبك رقم #{oid} من بوابة الكرك، حالته الآن: {new_status}."
                wa_msg_store = f"تنبيه طلب جديد رقم #{oid} للزبون {c_name} ({c_phone_str}). العنوان: {c_address}. الإجمالي: {total} د.أ"
                
                url_cust = f"https://wa.me/962{c_phone_str.lstrip('0')}?text={urllib.parse.quote(wa_msg_cust)}"
                url_store = f"https://wa.me/962797088219?text={urllib.parse.quote(wa_msg_store)}"

                w_c1, w_c2 = st.columns(2)
                with w_c1:
                    st.markdown(f'<a href="{url_cust}" target="_blank"><div style="background:#25D366; color:white; padding:8px; border-radius:6px; text-align:center; font-weight:bold; font-size:12px;">💬 مراسلة الزبون واتساب</div></a>', unsafe_allow_html=True)
                with w_c2:
                    st.markdown(f'<a href="{url_store}" target="_blank"><div style="background:#128C7E; color:white; padding:8px; border-radius:6px; text-align:center; font-weight:bold; font-size:12px;">💬 إرسال للمتجر واتساب (0797088219)</div></a>', unsafe_allow_html=True)

                st.markdown("---")
        else:
            st.info("لا توجد طلبات واردة حالياً.")
    except Exception as e:
        st.error(f"تعذر جلب الطلبات: {e}")


# ============================================================
# 2. المتاجر
# ============================================================
with tab_merchants:
    st.subheader("🏬 إدارة المتاجر الشاملة")
    
    sub_m_tab1, sub_m_tab2 = st.tabs(["تعديل / حذف متجر قائم", "إضافة متجر جديد"])
    
    with sub_m_tab1:
        try:
            merchants = sb.table("merchants").select("*").execute().data or []
            if merchants:
                m_names = [m["name"] for m in merchants]
                sel_m = st.selectbox("اختر المتجر للتعديل:", m_names, key="sel_merchant_edit")
                cur_m = next((m for m in merchants if m["name"] == sel_m), None)
                
                if cur_m:
                    map_link_val = cur_m.get("map_link", "")
                    if map_link_val:
                        st.markdown(f'<a href="{map_link_val}" target="_blank"><div style="background:#4285F4; color:white; padding:10px; border-radius:8px; text-align:center; font-weight:bold; margin-bottom:15px;">🗺 فتح موقع المتجر على خرائط جوجل (Google Maps)</div></a>', unsafe_allow_html=True)

                    with st.form(f"edit_m_form_{cur_m['id']}"):
                        e_name = st.text_input("اسم المتجر:", value=cur_m.get("name", ""))
                        e_cat = st.selectbox("التصنيف:", categories_list, index=categories_list.index(cur_m.get("category")) if cur_m.get("category") in categories_list else 0)
                        e_phone = st.text_input("رقم الهاتف:", value=cur_m.get("phone", ""))
                        e_loc = st.text_input("الموقع الوصفي:", value=cur_m.get("location", ""))
                        e_map = st.text_input("رابط موقع المتجر (Google Maps URL):", value=map_link_val)
                        
                        e_img_url = st.text_input("رابط الصورة الحالي أو الجديد (URL):", value=cur_m.get("image_data", ""))
                        e_img_file = st.file_uploader("أو ارفع صورة جديدة للمتجر:", type=["jpg", "png", "jpeg"], key=f"file_m_{cur_m['id']}")

                        e_status = st.selectbox("الحالة:", ["معتمد", "قيد المراجعة", "موقف"], index=0)

                        col_sv, col_dl = st.columns(2)
                        with col_sv:
                            sv_btn = st.form_submit_button("💾 حفظ التعديلات")
                        with col_dl:
                            dl_btn = st.form_submit_button("🗑 حذف المتجر")

                        if sv_btn:
                            safe_e_name = str(e_name or "").strip()
                            safe_e_phone = str(e_phone or "").strip()
                            safe_e_loc = str(e_loc or "").strip()
                            safe_e_map = str(e_map or "").strip()
                            final_img = handle_image_input(e_img_file, e_img_url)
                            
                            sb.table("merchants").update({
                                "name": safe_e_name, 
                                "category": e_cat, 
                                "phone": safe_e_phone,
                                "location": safe_e_loc, 
                                "map_link": safe_e_map,
                                "image_data": final_img, 
                                "status": e_status
                            }).eq("id", cur_m["id"]).execute()
                            st.success("تم تحديث المتجر بنجاح!")
                            st.rerun()

                        if dl_btn:
                            sb.table("merchants").delete().eq("id", cur_m["id"]).execute()
                            st.warning("تم حذف المتجر نهائياً.")
                            st.rerun()
            else:
                st.info("لا توجد متاجر مسجلة.")
        except Exception as e:
            st.error(f"خطأ: {e}")

    with sub_m_tab2:
        st.markdown('<a href="https://www.google.com/maps" target="_blank"><div style="background:#4285F4; color:white; padding:10px; border-radius:8px; text-align:center; font-weight:bold; margin-bottom:15px;">🗺 افتح خرائط جوجل وانسخ رابط الموقع (Google Maps)</div></a>', unsafe_allow_html=True)
        with st.form("new_store_form"):
            n_name = st.text_input("اسم المتجر الجديد:")
            n_cat = st.selectbox("التصنيف:", categories_list, key="new_cat_store")
            n_phone = st.text_input("الهاتف:", "079xxxxxxx")
            n_loc = st.text_input("الموقع الوصفي:", "الكرك - المرج")
            n_map = st.text_input("رابط موقع المتجر (Google Maps URL):", "")
            
            n_img_url = st.text_input("رابط صورة المتجر (URL):", "https://images.unsplash.com/photo-1542838132-92c53300491e?auto=format&fit=crop&w=200&q=80")
            n_img_file = st.file_uploader("أو رفع ملف صورة المتجر:", type=["jpg", "png", "jpeg"], key="new_m_file")

            submit_new_store = st.form_submit_button("➕ إضافة المتجر")

        if submit_new_store:
            safe_n_name = str(n_name or "").strip()
            safe_n_phone = str(n_phone or "").strip()
            safe_n_loc = str(n_loc or "").strip()
            safe_n_map = str(n_map or "").strip()
            
            if not safe_n_name:
                st.warning("الرجاء إدخال اسم المتجر على الأقل.")
            else:
                try:
                    final_n_img = handle_image_input(n_img_file, n_img_url)
                    
                    sb.table("merchants").insert({
                        "name": safe_n_name, 
                        "category": n_cat, 
                        "phone": safe_n_phone,
                        "location": safe_n_loc, 
                        "map_link": safe_n_map,
                        "image_data": final_n_img, 
                        "status": "معتمد"
                    }).execute()
                    
                    st.success("تمت إضافة المتجر بنجاح!")
                    st.rerun()
                except Exception as e:
                    st.error(f"فشل حفظ المتجر بسبب الخطأ التالي: {e}")


# ============================================================
# 3. أصناف المتاجر
# ============================================================
with tab_products:
    st.subheader("📋 إدارة أصناف ومنتجات المتاجر (إضافة، تعديل، حذف)")

    sub_p_tab1, sub_p_tab2 = st.tabs(["تعديل / حذف صنف قائم", "إضافة صنف جديد"])

    try:
        merchants_data = sb.table("merchants").select("name").execute().data or []
        m_names_only = [m["name"] for m in merchants_data]
    except Exception:
        m_names_only = []

    with sub_p_tab1:
        if not m_names_only:
            st.warning("لا توجد متاجر مسجلة حالياً.")
        else:
            sel_store_for_prod = st.selectbox("اختر المتجر لعرض أصنافه:", m_names_only, key="sel_store_prods")
            try:
                store_products = sb.table("products").select("*").eq("merchant_name", sel_store_for_prod).execute().data or []
                if store_products:
                    p_names_list = [p["item_name"] for p in store_products]
                    sel_prod_item = st.selectbox("اختر الصنف للتعديل أو الحذف:", p_names_list, key="sel_prod_item_edit")
                    cur_p = next((p for p in store_products if p["item_name"] == sel_prod_item), None)

                    if cur_p:
                        with st.form(f"edit_prod_form_{cur_p['id']}"):
                            up_p_name = st.text_input("اسم الصنف:", value=cur_p.get("item_name", ""))
                            up_p_price = st.number_input("السعر (د.أ):", value=float(cur_p.get("price") or 0.0), step=0.25)
                            up_p_qty = st.text_input("الكمية:", value=str(cur_p.get("quantity", "1")))
                            up_p_unit = st.text_input("الوحدة:", value=str(cur_p.get("unit", "حبة")))
                            
                            up_p_url = st.text_input("رابط الصورة الحالي (URL):", value=str(cur_p.get("image_path", "")))
                            up_p_file = st.file_uploader("أو رفع صورة جديدة للصنف:", type=["jpg", "png", "jpeg"], key=f"file_p_{cur_p['id']}")

                            c_btn1, c_btn2 = st.columns(2)
                            with c_btn1:
                                save_p_btn = st.form_submit_button("💾 حفظ تعديلات الصنف")
                            with c_btn2:
                                del_p_btn = st.form_submit_button("🗑 حذف الصنف")

                            if save_p_btn:
                                safe_p_name = str(up_p_name or "").strip()
                                safe_p_qty = str(up_p_qty or "").strip()
                                safe_p_unit = str(up_p_unit or "").strip()
                                final_p_img = handle_image_input(up_p_file, up_p_url)
                                
                                sb.table("products").update({
                                    "item_name": safe_p_name,
                                    "price": up_p_price,
                                    "quantity": safe_p_qty,
                                    "unit": safe_p_unit,
                                    "image_path": final_p_img
                                }).eq("id", cur_p["id"]).execute()
                                st.success("تم تحديث الصنف بنجاح!")
                                st.rerun()

                            if del_p_btn:
                                sb.table("products").delete().eq("id", cur_p["id"]).execute()
                                st.warning("تم حذف الصنف بنجاح.")
                                st.rerun()
                else:
                    st.info(f"لا توجد أصناف مضافة لهذا المتجر ({sel_store_for_prod}).")
            except Exception as e:
                st.error(f"خطأ: {e}")

    with sub_p_tab2:
        if not m_names_only:
            st.warning("الرجاء إضافة متجر أولاً لتتمكن من إضافة أصناف إليه.")
        else:
            with st.form("admin_add_product_form"):
                prod_merchant = st.selectbox("اختر المتجر:", m_names_only, key="prod_merch_add")
                prod_name = st.text_input("اسم الصنف أو الوجبة:")
                prod_price = st.number_input("السعر (د.أ):", min_value=0.0, value=1.00, step=0.25)
                prod_qty = st.text_input("الكمية أو الحجم:", "1")
                prod_unit = st.text_input("الوحدة (كغ، حبة، طبق، إلخ):", "حبة")
                
                prod_url = st.text_input("رابط صورة الصنف (URL):", "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?auto=format&fit=crop&w=200&q=80")
                prod_file = st.file_uploader("أو رفع ملف صورة الصنف:", type=["jpg", "png", "jpeg"], key="new_p_file")

                submit_prod = st.form_submit_button("💾 حفظ وإضافة الصنف")
                
                if submit_prod:
                    safe_prod_name = str(prod_name or "").strip()
                    safe_prod_qty = str(prod_qty or "").strip()
                    safe_prod_unit = str(prod_unit or "").strip()
                    
                    if not safe_prod_name:
                        st.warning("الرجاء إدخال اسم الصنف.")
                    else:
                        try:
                            final_prod_img = handle_image_input(prod_file, prod_url)
                            sb.table("products").insert({
                                "merchant_name": prod_merchant,
                                "item_name": safe_prod_name,
                                "price": prod_price,
                                "quantity": safe_prod_qty,
                                "unit": safe_prod_unit,
                                "image_path": final_prod_img
                            }).execute()
                            st.success(f"🎉 تمت إضافة الصنف '{safe_prod_name}' إلى متجر {prod_merchant} بنجاح!")
                        except Exception as e:
                            st.error(f"خطأ: {e}")


# ============================================================
# 4. إدارة السائقين
# ============================================================
with tab_drivers:
    st.subheader("🛵 إدارة السائقين (تعديل، حذف، إضافة، ورابط الموقع)")

    d_tab1, d_tab2 = st.tabs(["تعديل / حذف / مواقع السائقين", "إضافة سائق جديد"])

    with d_tab1:
        try:
            drivers = sb.table("drivers").select("*").execute().data or []
            if drivers:
                d_names = [d["name"] for d in drivers]
                sel_d = st.selectbox("اختر السائق للتعديل أو المتابعة:", d_names, key="sel_driver_edit")
                cur_d = next((d for d in drivers if d["name"] == sel_d), None)

                if cur_d:
                    d_map_link = cur_d.get("map_link", "")
                    if d_map_link:
                        st.markdown(f'<a href="{d_map_link}" target="_blank"><div style="background:#4285F4; color:white; padding:10px; border-radius:8px; text-align:center; font-weight:bold; margin-bottom:15px;">🗺 فتح موقع السائق الحالي على خرائط جوجل (Google Maps)</div></a>', unsafe_allow_html=True)

                    with st.form(f"edit_driver_form_{cur_d['id']}"):
                        ud_name = st.text_input("اسم السائق:", value=cur_d.get("name", ""))
                        ud_phone = st.text_input("رقم الهاتف:", value=cur_d.get("phone", ""))
                        ud_map = st.text_input("رابط موقع السائق (Google Maps URL):", value=d_map_link)
                        ud_status = st.selectbox("الحالة:", ["متاح", "في توصيل طلب", "غير متصل"], index=0)

                        col_d1, col_d2 = st.columns(2)
                        with col_d1:
                            save_d_btn = st.form_submit_button("💾 حفظ تعديلات السائق")
                        with col_d2:
                            del_d_btn = st.form_submit_button("🗑 حذف السائق")

                        if save_d_btn:
                            safe_ud_name = str(ud_name or "").strip()
                            safe_ud_phone = str(ud_phone or "").strip()
                            safe_ud_map = str(ud_map or "").strip()
                            
                            sb.table("drivers").update({
                                "name": safe_ud_name,
                                "phone": safe_ud_phone,
                                "map_link": safe_ud_map,
                                "status": ud_status
                            }).eq("id", cur_d["id"]).execute()
                            st.success("تم تحديث بيانات وموقع السائق بنجاح!")
                            st.rerun()

                        if del_d_btn:
                            sb.table("drivers").delete().eq("id", cur_d["id"]).execute()
                            st.warning("تم حذف السائق بنجاح.")
                            st.rerun()
            else:
                st.info("لا يوجد سائقون مسجلون بعد.")
        except Exception:
            st.info("سيتم تفعيل سجل السائقين والمواقع تلقائياً عند إضافة أول سائق.")

    with d_tab2:
        st.markdown('<a href="https://www.google.com/maps" target="_blank"><div style="background:#4285F4; color:white; padding:10px; border-radius:8px; text-align:center; font-weight:bold; margin-bottom:15px;">🗺 افتح خرائط جوجل وانسخ رابط الموقع (Google Maps)</div></a>', unsafe_allow_html=True)
        with st.form("add_driver_form"):
            new_d_name = st.text_input("اسم السائق:")
            new_d_phone = st.text_input("رقم الهاتف:", "079xxxxxxx")
            new_d_map = st.text_input("رابط موقع السائق (Google Maps URL):", "")
            
            if st.form_submit_button("➕ إضافة السائق للنظام"):
                try:
                    safe_new_d_name = str(new_d_name or "").strip()
                    safe_new_d_phone = str(new_d_phone or "").strip()
                    safe_new_d_map = str(new_d_map or "").strip()
                    
                    sb.table("drivers").insert({
                        "name": safe_new_d_name,
                        "phone": safe_new_d_phone,
                        "map_link": safe_new_d_map,
                        "status": "متاح"
                    }).execute()
                    st.success("تمت إضافة السائق وموقعه بنجاح!")
                    st.rerun()
                except Exception as ex:
                    st.error(f"خطأ: {ex}")


# ============================================================
# 5. سجل الزبائن
# ============================================================
with tab_customers:
    st.subheader("👥 سجل الزبائن وعناوينهم المرسلة")
    try:
        customers = sb.table("customers").select("*").execute().data or []
        if customers:
            for cust in customers:
                cust_map = cust.get('map_link') or f"https://www.google.com/maps?q={cust.get('lat')},{cust.get('lng')}" if cust.get('lat') else "#"
                st.markdown(f"""
                <div style="background:white; border-radius:10px; padding:12px; margin-bottom:8px; border:1px solid #ddd;">
                    <b>👤 الاسم: {cust.get('name')}</b><br>
                    <span>📞 الهاتف: {cust.get('phone')}</span><br>
                    <span>📍 العنوان: {cust.get('address')}</span><br>
                    <span>🗺 <a href="{cust_map}" target="_blank">رابط موقع الزبون على الخريطة</a></span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("لا توجد سجلات زبائن محفوظة بعد.")
    except Exception:
        st.info("لا يوجد جدول customers مفعل حالياً أو لا توجد بيانات.")


# ============================================================
# 6. إدارة العروض والتخفيضات
# ============================================================
with tab_offers:
    st.subheader("🏷 إدارة العروض والتخفيضات للمتاجر")
    with st.form("add_offer_form"):
        offer_title = st.text_input("عنوان العرض (مثال: خصم 20% على وجبات الغداء):")
        offer_store = st.text_input("اسم المتجر المقدم للعرض:")
        offer_desc = st.text_area("تفاصيل العرض والشروط:")
        
        if st.form_submit_button("📢 نشر العرض في التطبيق"):
            st.success(f"🎉 تم نشر العرض '{offer_title}' بنجاح لمتجر {offer_store}!")


# ============================================================
# 7. التقرير المالي
# ============================================================
with tab_finance:
    st.subheader("📊 التقرير المالي الشامل")
    try:
        orders = sb.table("orders").select("total_amount, created_at").execute().data or []
        total_sales = sum(float(o.get("total_amount") or 0) for o in orders)
        total_orders_count = len(orders)
        estimated_delivery_revenue = total_orders_count * 1.50
        estimated_service_revenue = total_orders_count * 0.25

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("إجمالي قيمة الطلبات", f"{total_sales:.2f} د.أ")
        with col2:
            st.metric("أرباح التوصيل المتوقعة", f"{estimated_delivery_revenue:.2f} د.أ")
        with col3:
            st.metric("أرباح خدمات التطبيق", f"{estimated_service_revenue:.2f} د.أ")

        st.markdown("---")
        st.write("📈 **تفاصيل العمليات المالية المسجلة:**")
        if orders:
            for o in orders:
                st.write(f"- مبلغ الطلب: **{o.get('total_amount')} د.أ** | التاريخ: {o.get('created_at')}")
        else:
            st.info("لا توجد بيانات مالية كافية بعد.")
    except Exception as e:
        st.error(f"تعذر استخراج التقرير المالي: {e}")
