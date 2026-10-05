import sys
import io
import base64
from datetime import datetime
import urllib.parse

import streamlit as st
from supabase import create_client


# ============================================================
# دالة إرسال رسائل الواتساب (الإدارة)
# ============================================================
def send_whatsapp_alert(phone_number, message_text):
    encoded_message = urllib.parse.quote(message_text)
    whatsapp_url = f"https://wa.me/{phone_number}?text={encoded_message}"
    return whatsapp_url

def process_new_order_admin(customer_order_text, driver_phone_number, customer_phone, customer_address, merchant_name, merchant_phone, merchant_location, delivery_fee, total_amount):
    admin_merchant_phone = "962797088219"
    
    merchant_msg = f"بوابة الطلبات ترحب بكم، ارجو تجهيز الطلب:\n{customer_order_text}"
    
    driver_msg = (
        f"🚨 يرجى التوجه فوراً لاستلام الطلب من:\n"
        f"🏬 اسم المتجر: {merchant_name}\n"
        f"📞 هاتف المتجر: {merchant_phone}\n"
        f"📍 موقع/عنوان المتجر: {merchant_location}\n\n"
        f"📋 تفاصيل الطلب:\n{customer_order_text}\n\n"
        f"💰 أجور التوصيل للمتجر: {delivery_fee:.2f} د.أ\n"
        f"💵 إجمالي الطلب المطلوب تحصيله: {total_amount:.2f} د.أ\n\n"
        f"📍 تفاصيل توصيل الزبون:\n"
        f"👤 الهاتف: {customer_phone}\n"
        f"📍 العنوان: {customer_address}"
    )
    
    merchant_link = send_whatsapp_alert(admin_merchant_phone, merchant_msg)
    driver_link = send_whatsapp_alert(driver_phone_number, driver_msg)
    
    return merchant_link, driver_link


# ============================================================
# إعداد الصفحة وتحديد وضع التطبيق (زبون / إحالة / إدارة)
# ============================================================
st.set_page_config(
    page_title="بوابة الطلبات الشاملة",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="collapsed"
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
# التحقق هل المستخدم زبون أم مدير النظام
# ============================================================
query_params = st.query_params
is_admin_mode = query_params.get("mode") == "admin"


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
# 1. واجهة الزبون (Customer View)
# ============================================================
if not is_admin_mode:
    st.markdown("""
    <div style="text-align: center; padding: 10px; background: linear-gradient(135deg, #10B981, #059669); color: white; border-radius: 12px; margin-bottom: 20px;">
        <h2 style="margin:0; font-weight:800;">🛒 منصة الطلبات والتوصيل الشاملة</h2>
        <p style="margin:5px 0 0 0; font-size: 14px;">اطلب احتياجاتك من أفضل المتاجر والمطاعم بكل سهولة</p>
    </div>
    """, unsafe_allow_html=True)

    try:
        merchants_data = sb.table("merchants").select("*").execute().data or []
    except Exception:
        merchants_data = []

    if not merchants_data:
        st.warning("لا توجد متاجر متاحة حالياً. يرجى العودة لاحقاً أو الدخول للوحة الإدارة لإضافة متاجر.")
    else:
        categories_list = list(set([m.get("category", "عام") for m in merchants_data]))
        selected_cat = st.selectbox("📁 اختر التصنيف:", ["الكل"] + categories_list)

        filtered_merchants = merchants_data if selected_cat == "الكل" else [m for m in merchants_data if m.get("category") == selected_cat]

        st.markdown("### 🏬 المتاجر المتاحة:")
        merchant_names = [m["name"] for m in filtered_merchants]
        chosen_merchant_name = st.selectbox("اختر المتجر المطلوب:", merchant_names)

        selected_merchant_obj = next((m for m in filtered_merchants if m["name"] == chosen_merchant_name), None)

        if selected_merchant_obj:
            # قراءة أجور التوصيل الديناميكية الخاصة بالمتجر من جدول merchants
            try:
                store_delivery_fee = float(selected_merchant_obj.get("delivery_fee", 1.50) or 1.50)
            except Exception:
                store_delivery_fee = 1.50

            st.markdown(f"""
            <div style="background: white; padding: 15px; border-radius: 10px; border: 1px solid #E5E7EB; margin-bottom: 15px;">
                <h4 style="margin:0; color:#1F2937;">{selected_merchant_obj.get('name')}</h4>
                <p style="margin:5px 0; color:#4B5563; font-size:13px;">📍 الموقع: {selected_merchant_obj.get('location', 'غير محدد')} | 📞 الهاتف: {selected_merchant_obj.get('phone', 'غير محدد')}</p>
                <p style="margin:0; color:#059669; font-weight:bold; font-size:14px;">🚚 أجور التوصيل لهذا المتجر: {store_delivery_fee:.2f} د.أ</p>
            </div>
            """, unsafe_allow_html=True)

            try:
                products = sb.table("products").select("*").eq("merchant_name", chosen_merchant_name).execute().data or []
            except Exception:
                products = []

            if not products:
                st.info("لا توجد أصناف مضافة لهذا المتجر حالياً.")
            else:
                st.markdown("#### 📋 أصناف المتجر:")
                if "cart" not in st.session_state:
                    st.session_state.cart = {}

                for prod in products:
                    p_id = prod["id"]
                    p_name = prod["item_name"]
                    p_price = float(prod.get("price") or 0.0)
                    p_unit = prod.get("unit", "حبة")

                    col_p1, col_p2, col_p3 = st.columns([3, 2, 2])
                    with col_p1:
                        st.write(f"**{p_name}**")
                        st.caption(fالسعر: {p_price:.2f} د.أ / {p_unit})
                    with col_p2:
                        qty = st.number_input(f"الكمية ({p_name})", min_value=0, max_value=50, value=0, key=f"prod_qty_{p_id}")
                        if qty > 0:
                            st.session_state.cart[p_name] = {"price": p_price, "qty": qty, "unit": p_unit}
                        elif p_name in st.session_state.cart:
                            del st.session_state.cart[p_name]

                if st.session_state.cart:
                    st.markdown("---")
                    st.markdown("#### 🛒 سلة المشتريات الخاصة بك:")
                    subtotal = 0.0
                    order_summary_lines = [f"[{chosen_merchant_name}]"]
                    for item_name, info in st.session_state.cart.items():
                        item_total = info["price"] * info["qty"]
                        subtotal += item_total
                        order_summary_lines.append(- {item_name}: {info['qty']} {info['unit']} (الإجمالي: {item_total:.2f} د.أ))
                    
                    final_total_calc = subtotal + store_delivery_fee
                    st.write(f"💰 مجموع المنتجات: **{subtotal:.2f} د.أ**")
                    st.write(f"🚚 أجور التوصيل: **{store_delivery_fee:.2f} د.أ**")
                    st.write(f"💵 **الإجمالي الكلي المطلوب دفعه: {final_total_calc:.2f} د.أ**")

                    with st.form("customer_checkout_form"):
                        st.markdown("##### 📍 بيانات التوصيل:")
                        c_name_input = st.text_input("الاسم الكريم:")
                        c_phone_input = st.text_input("رقم الهاتف (مثال: 079xxxxxxx):")
                        # تم إزالة القيد الجغرافي السابق وأصبح الحقل حراً بالكامل
                        c_address_input = st.text_input("العنوان بالتفصيل (المدينة، المنطقة، الشارع، رقم البناية):", placeholder="مثال: عمان، الدوار السابع، شارع مدحت الحبيب...")
                        c_map_input = st.text_input("رابط موقعك على خرائط جوجل (اختياري - Google Maps URL):", "")
                        c_payment_method = st.selectbox("طريقة الدفع:", ["الدفع نقداً عند الاستلام", "محفظة إلكترونية / زين كاش"])

                        submit_order_btn = st.form_submit_button("🚀 إرسال الطلب واعتماده")

                        if submit_order_btn:
                            safe_c_name = str(c_name_input or "").strip()
                            safe_c_phone = str(c_phone_input or "").strip()
                            safe_c_address = str(c_address_input or "").strip()

                            if not safe_c_name or not safe_c_phone or not safe_c_address:
                                st.warning("الرجاء إدخال الاسم، رقم الهاتف، وعنوان التوصيل بشكل كامل.")
                            else:
                                full_details_str = "\n".join(order_summary_lines)
                                try:
                                    # حفظ الزبون في جدول customers
                                    try:
                                        sb.table("customers").insert({
                                            "name": safe_c_name,
                                            "phone": safe_c_phone,
                                            "address": safe_c_address,
                                            "map_link": c_map_input
                                        }).execute()
                                    except Exception:
                                        pass

                                    # حفظ الطلب في جدول orders
                                    res_order = sb.table("orders").insert({
                                        "customer_name": safe_c_name,
                                        "customer_phone": safe_c_phone,
                                        "customer_address": safe_c_address,
                                        "order_details": full_details_str,
                                        "total_amount": final_total_calc,
                                        "payment_method": c_payment_method,
                                        "order_status": "قيد التجهيز"
                                    }).execute()

                                    st.success("🎉 تم إرسال طلبك بنجاح! سيتم التواصل معك وتجهيز طلبك فوراً.")
                                    st.balloons()
                                    st.session_state.cart = {}
                                except Exception as e:
                                    st.error(f"حدث خطأ أثناء إرسال الطلب: {e}")

    st.markdown("---")
    st.markdown(f'<div style="text-align:center;"><a href="?mode=admin" target="_self">⚙ الانتقال إلى لوحة الإدارة</a></div>', unsafe_allow_html=True)


# ============================================================
# 2. لوحة إدارة النظام الشاملة (Admin Panel)
# ============================================================
else:
    st.markdown(
        """
        <div style="background: linear-gradient(135deg, #2D3142, #4F5D75); border-radius: 12px; padding: 15px 20px; margin-bottom: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
            <div style="color: white; font-size: 22px; font-weight: 800; margin: 0;">⚙ لوحة إدارة بوابة الطلبات الشاملة</div>
            <div style="color: #E0E0E0; font-size: 12px; margin: 0;">Administration Panel • إدارة المتاجر، الأصناف، السائقين، والطلبات</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    categories_list = [
        "مطاعم", "حلويات", "ماركت", "محامص ومكسرات", 
        "خضروات وفواكه", "لحوم", "صيدليات ومستلزمات طبيه"
    ]

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

    # ------------------------------------------------------------
    # 1. الطلبات والتنبيهات (إدارة)
    # ------------------------------------------------------------
    with tab_orders:
        st.subheader("📦 متابعة الطلبات الواردة وتحديد أجور التوصيل")
        
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
            drivers_data = sb.table("drivers").select("name, phone").execute().data or []
            drivers_list = [d["name"] for d in drivers_data] if drivers_data else ["لا توجد سائقون مسجلون"]
            
            try:
                merchants_data = sb.table("merchants").select("*").execute().data or []
            except Exception:
                merchants_data = []

            if orders:
                sub_o_tabs = st.tabs(["🔴 قيد التجهيز / جديدة", "🔵 جاري التوصيل", "🟢 المكتملة", "⚪ الكل"])
                
                new_or_prep_orders = [o for o in orders if o.get("order_status", "قيد التجهيز") in ["قيد التجهيز", ""]]
                delivering_orders = [o for o in orders if o.get("order_status") == "جاري التوصيل"]
                completed_orders = [o for o in orders if o.get("order_status") in ["تم التوصيل", "ملغي"]]
                
                tab_containers = [sub_o_tabs[0], sub_o_tabs[1], sub_o_tabs[2], sub_o_tabs[3]]
                lists_to_render = [new_or_prep_orders, delivering_orders, completed_orders, orders]
                
                for t_idx, current_orders_list in enumerate(lists_to_render):
                    with tab_containers[t_idx]:
                        if not current_orders_list:
                            st.info("لا توجد طلبات في هذا القسم حالياً.")
                            continue
                            
                        for ord_item in current_orders_list:
                            oid = ord_item.get("id")
                            c_name = ord_item.get("customer_name")
                            c_phone = ord_item.get("customer_phone")
                            c_address = ord_item.get("customer_address")
                            base_total = float(ord_item.get("total_amount") or 0.0)
                            status = ord_item.get("order_status", "قيد التجهيز")
                            details = ord_item.get("order_details", "")
                            payment = ord_item.get("payment_method")
                            created_at = ord_item.get("created_at", "غير محدد")
                            
                            m_name_extracted = "متجر بوابة الطلبات"
                            m_phone_extracted = "0797088219"
                            m_loc_extracted = "عمان"
                            default_merchant_fee = 1.50
                            
                            for m in merchants_data:
                                m_n = m.get("name", "").strip()
                                if m_n and (m_n in str(details) or f"[{m_n}]" in str(details) or f"المتجر: {m_n}" in str(details)):
                                    m_name_extracted = m_n
                                    m_phone_extracted = m.get("phone", "0797088219")
                                    m_loc_extracted = m.get("location", "عمان")
                                    try:
                                        default_merchant_fee = float(m.get("delivery_fee", 1.50) or 1.50)
                                    except Exception:
                                        default_merchant_fee = 1.50
                                    break
                            
                            if m_name_extracted == "متجر بوابة الطلبات" and "[" in str(details) and "]" in str(details):
                                try:
                                    start_idx = str(details).index("[") + 1
                                    end_idx = str(details).index("]")
                                    extracted_candidate = str(details)[start_idx:end_idx].strip()
                                    if extracted_candidate:
                                        m_name_extracted = extracted_candidate
                                except Exception:
                                    pass

                            st.markdown(f"""
                            <div style="background:white; border-radius:12px; padding:15px; margin-bottom:12px; border:1px solid #D1D5DB; box-shadow: 0 2px 8px rgba(0,0,0,0.04);">
                                <div style="display:flex; justify-content:space-between; align-items:center;">
                                    <b>الطلب #{oid} — الزبون: {c_name} ({c_phone})</b>
                                    <span style="font-size:11px; color:#666;">🕒 وقت الطلب: {created_at}</span>
                                </div>
                                <span style="display:block; margin-top:5px;">📍 عنوان الزبون: {c_address}</span>
                                <span style="display:block; margin-top:3px;">🏬 المتجر المرتبط: <b>{m_name_extracted}</b></span>
                                <span style="display:block; margin-top:3px;">💰 قيمة المنتجات: <b>{base_total} د.أ</b> | الدفع: {payment} | الحالة: <b>{status}</b></span>
                            </div>
                            """, unsafe_allow_html=True)

                            with st.expander(f"📋 تفاصيل أصناف الطلب #{oid} ونسخ النص", expanded=False):
                                st.text_area(f"النص الخام للطلب #{oid}", value=details, height=80, key=f"raw_txt_unique_{t_idx}_{oid}")

                            col_fee, col_stat, col_drv = st.columns([2, 2, 2])
                            with col_fee:
                                custom_delivery_fee = st.number_input(
                                    "أجور التوصيل (د.أ):", 
                                    min_value=0.0, 
                                    value=default_merchant_fee, 
                                    step=0.25, 
                                    key=f"fee_unique_{t_idx}_{oid}", 
                                    help="أجور التوصيل الافتراضية للمتجر، ويمكن تعديلها حسب المسافة"
                                )
                            with col_stat:
                                new_status = st.selectbox(
                                    "تحديث الحالة:", 
                                    ["قيد التجهيز", "جاري التوصيل", "تم التوصيل", "ملغي"], 
                                    key=f"st_unique_{t_idx}_{oid}", 
                                    index=["قيد التجهيز", "جاري التوصيل", "تم التوصيل", "ملغي"].index(status) if status in ["قيد التجهيز", "جاري التوصيل", "تم التوصيل", "ملغي"] else 0
                                )
                            with col_drv:
                                assigned_driver = st.selectbox("تعيين سائق:", drivers_list, key=f"drv_unique_{t_idx}_{oid}")

                            final_order_total = base_total + custom_delivery_fee

                            if st.button(f"💾 حفظ واعتماد الفاتورة وتحديث الطلب #{oid}", key=f"btn_upd_unique_{t_idx}_{oid}", use_container_width=True):
                                try:
                                    sb.table("orders").update({
                                        "order_status": new_status,
                                        "driver_name": assigned_driver,
                                        "total_amount": final_order_total
                                    }).eq("id", oid).execute()
                                    st.success("تم اعتماد الفاتورة وتحديث الطلب بنجاح!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"خطأ: {e}")

                            c_phone_str = str(c_phone or "")
                            selected_driver_obj = next((d for d in drivers_data if d["name"] == assigned_driver), None)
                            drv_phone_str = str(selected_driver_obj.get("phone", "962790000000") if selected_driver_obj else "962790000000")

                            url_store, url_driver = process_new_order_admin(
                                details or "", 
                                drv_phone_str, 
                                c_phone_str, 
                                c_address or "",
                                m_name_extracted,
                                m_phone_extracted,
                                m_loc_extracted,
                                custom_delivery_fee,
                                final_order_total
                            )
                            
                            wa_msg_cust = f"مرحباً {c_name}، بخصوص طلبك رقم #{oid}، أجور التوصيل: {custom_delivery_fee} د.أ والإجمالي الكلي للفاتورة: {final_order_total} د.أ، حالته الآن: {new_status}."
                            url_cust = f"https://wa.me/962{c_phone_str.lstrip('0')}?text={urllib.parse.quote(wa_msg_cust)}"

                            w_c1, w_c2, w_c3 = st.columns(3)
                            with w_c1:
                                st.markdown(f'<a href="{url_cust}" target="_blank"><div style="background:#25D366; color:white; padding:8px; border-radius:6px; text-align:center; font-weight:bold; font-size:12px;">💬 مراسلة الزبون بالفاتورة</div></a>', unsafe_allow_html=True)
                            with w_c2:
                                st.markdown(f'<a href="{url_store}" target="_blank"><div style="background:#128C7E; color:white; padding:8px; border-radius:6px; text-align:center; font-weight:bold; font-size:12px;">💬 إرسال للتاجر (0797088219)</div></a>', unsafe_allow_html=True)
                            with w_c3:
                                st.markdown(f'<a href="{url_driver}" target="_blank"><div style="background:#075E54; color:white; padding:8px; border-radius:6px; text-align:center; font-weight:bold; font-size:12px;">💬 إرسال للسائق (مع التوصيل)</div></a>', unsafe_allow_html=True)

                            st.markdown("---")
            else:
                st.info("لا توجد طلبات واردة حالياً.")
        except Exception as e:
            st.error(f"تعذر جلب الطلبات: {e}")

    # ------------------------------------------------------------
    # 2. المتاجر (إدارة)
    # ------------------------------------------------------------
    with tab_merchants:
        st.subheader("🏬 إدارة المتاجر الشاملة وتحديد أجور التوصيل الافتراضية")
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
                            e_loc = st.text_input("الموقع الوصفي (المدينة / المنطقة):", value=cur_m.get("location", ""))
                            
                            e_del_fee = st.number_input("أجور التوصيل الافتراضية للمتجر (د.أ):", min_value=0.0, value=float(cur_m.get("delivery_fee", 1.50) or 1.50), step=0.25)
                            
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
                                
                                update_payload = {
                                    "name": safe_e_name, 
                                    "category": e_cat, 
                                    "phone": safe_e_phone,
                                    "location": safe_e_loc,
                                    "map_link": safe_e_map,
                                    "image_data": final_img, 
                                    "status": e_status,
                                    "delivery_fee": e_del_fee
                                }
                                sb.table("merchants").update(update_payload).eq("id", cur_m["id"]).execute()
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
                n_loc = st.text_input("الموقع الوصفي (المدينة / المنطقة):", "عمان - الدوار السابع")
                n_del_fee = st.number_input("أجور التوصيل الافتراضية للمتجر (د.أ):", min_value=0.0, value=1.50, step=0.25)
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
                        insert_payload = {
                            "name": safe_n_name, 
                            "category": n_cat, 
                            "phone": safe_n_phone,
                            "location": safe_n_loc, 
                            "map_link": safe_n_map,
                            "image_data": final_n_img, 
                            "status": "معتمد",
                            "delivery_fee": n_del_fee
                        }
                        sb.table("merchants").insert(insert_payload).execute()
                        st.success("تمت إضافة المتجر بنجاح!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"فشل حفظ المتجر بسبب الخطأ التالي: {e}")

    # ------------------------------------------------------------
    # 3. أصناف المتاجر (إدارة)
    # ------------------------------------------------------------
    with tab_products:
        st.subheader("📋 إدارة أصناف ومنتجات المتاجر")
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
                    prod_unit = st.text_input("الوحدة:", "حبة")
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
                                st.success(f"🎉 تمت إضافة الصنف '{safe_prod_name}' بنجاح!")
                            except Exception as e:
                                st.error(f"خطأ: {e}")

    # ------------------------------------------------------------
    # 4. إدارة السائقين (إدارة)
    # ------------------------------------------------------------
    with tab_drivers:
        st.subheader("🛵 إدارة السائقين")
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
                                sb.table("drivers").update({
                                    "name": str(ud_name or "").strip(),
                                    "phone": str(ud_phone or "").strip(),
                                    "map_link": str(ud_map or "").strip(),
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
                st.info("سيتم تفعيل سجل السائقين تلقائياً عند إضافة أول سائق.")

        with d_tab2:
            st.markdown('<a href="https://www.google.com/maps" target="_blank"><div style="background:#4285F4; color:white; padding:10px; border-radius:8px; text-align:center; font-weight:bold; margin-bottom:15px;">🗺 افتح خرائط جوجل وانسخ رابط الموقع (Google Maps)</div></a>', unsafe_allow_html=True)
            with st.form("add_driver_form"):
                new_d_name = st.text_input("اسم السائق:")
                new_d_phone = st.text_input("رقم الهاتف:", "079xxxxxxx")
                new_d_map = st.text_input("رابط موقع السائق (Google Maps URL):", "")
                
                if st.form_submit_button("➕ إضافة السائق للنظام"):
                    try:
                        sb.table("drivers").insert({
                            "name": str(new_d_name or "").strip(),
                            "phone": str(new_d_phone or "").strip(),
                            "map_link": str(new_d_map or "").strip(),
                            "status": "متاح"
                        }).execute()
                        st.success("تمت إضافة السائق بنجاح!")
                        st.rerun()
                    except Exception as ex:
                        st.error(f"خطأ: {ex}")

    # ------------------------------------------------------------
    # 5. سجل الزبائن (إدارة)
    # ------------------------------------------------------------
    with tab_customers:
        st.subheader("👥 سجل الزبائن وعناوينهم المرسلة")
        try:
            customers = sb.table("customers").select("*").execute().data or []
            if customers:
                for cust in customers:
                    cust_map = cust.get('map_link') or "#"
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
            st.info("لا يوجد جدول customers مفعل حالياً.")

    # ------------------------------------------------------------
    # 6. إدارة العروض والتخفيضات (إدارة)
    # ------------------------------------------------------------
    with tab_offers:
        st.subheader("🏷 إدارة العروض والتخفيضات للمتاجر")
        with st.form("add_offer_form"):
            offer_title = st.text_input("عنوان العرض:")
            offer_store = st.text_input("اسم المتجر:")
            offer_desc = st.text_area("تفاصيل العرض:")
            if st.form_submit_button("📢 نشر العرض في التطبيق"):
                st.success("🎉 تم نشر العرض بنجاح!")

    # ------------------------------------------------------------
    # 7. التقرير المالي (إدارة)
    # ------------------------------------------------------------
    with tab_finance:
        st.subheader("📊 التقرير المالي الشامل")
        try:
            orders = sb.table("orders").select("total_amount, created_at").execute().data or []
            total_sales = sum(float(o.get("total_amount") or 0) for o in orders)
            total_orders_count = len(orders)
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("إجمالي قيمة الطلبات", f"{total_sales:.2f} د.أ")
            with col2:
                st.metric("عدد الطلبات الكلي", total_orders_count)

            st.markdown("---")
            if orders:
                for o in orders:
                    st.write(f"- مبلغ الطلب: **{o.get('total_amount')} د.أ** | التاريخ: {o.get('created_at')}")
            else:
                st.info("لا توجد بيانات مالية كافية بعد.")
        except Exception as e:
            st.error(f"تعذر استخراج التقرير المالي: {e}")

    st.markdown("---")
    st.markdown(f'<div style="text-align:center;"><a href="?" target="_self">🛒 العودة إلى واجهة الزبون الرئيسية</a></div>', unsafe_allow_html=True)
