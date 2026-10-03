import os
import re
import base64
import streamlit as st
from supabase import create_client

st.set_page_config(
    page_title="بوابة المتاجر - Karak Gate", page_icon="🔔", layout="wide"
)

st.markdown(
    """
    <style>
    #MainMenu {visibility: hidden;}
    .stDeployButton {display: none;}
    header {visibility: hidden;}
    footer {visibility: hidden;}

    .stApp {
        background-color: #FF5722 !important;
        color: #000000 !important;
    }
    h1, h2, h3, h4, h5, h6, p, label, span {
        color: #000000 !important;
    }
    .stButton>button {
        border-radius: 8px;
        font-weight: bold;
        border: none;
        background-color: #FFFFFF !important;
        color: #FF5722 !important;
    }
    .stButton>button:hover {
        background-color: #FFF3E0 !important;
        color: #E64A19 !important;
    }
    .merchant-card {
        background-color: #FFFFFF;
        padding: 20px;
        border-radius: 12px;
        margin-bottom: 15px;
        border: 2px solid #E0E0E0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .merchant-card h4, .merchant-card p, .merchant-card span {
        color: #000000 !important;
    }
    .item-card {
        background-color: #FFF3E0;
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 10px;
        border: 1px solid #FFCC80;
    }
    .item-card p {
        color: #000000 !important;
    }
    @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.05); }
        100% { transform: scale(1); }
    }
    .bell-alert {
        background-color: #B71C1C;
        color: white !important;
        padding: 15px;
        border-radius: 10px;
        text-align: center;
        font-weight: bold;
        font-size: 20px;
        animation: pulse 1s infinite;
        margin-bottom: 20px;
        border: 2px solid yellow;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# إعداد Supabase
SUPABASE_URL = "https://tzkdxodvlzggmcntnqer.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InR6a2R4b2R2bHpnZ21jbnRucWVyIiwicm9sZSI6ImFub24iLWV4cCI6MjEwNjUwOTczOX0.M944yHglTXVyPrxySSQj0MBaqpr2I_8ub7Uoofbd2_4"

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

# دالة تحويل الصورة المرفوعة إلى Base64 للتخزين المباشر في Supabase
def process_uploaded_image(uploaded_file):
    if uploaded_file is not None:
        try:
            bytes_data = uploaded_file.getvalue()
            b64_str = base64.b64encode(bytes_data).decode("utf-8")
            ext = uploaded_file.name.split(".")[-1].lower()
            mime = "image/png" if ext == "png" else "image/jpeg"
            return f"data:{mime};base64,{b64_str}"
        except Exception:
            return ""
    return ""

st.title("🏬 بوابة المتاجر الشاملة - Karak Gate")

if "merchant_step" not in st.session_state:
    st.session_state.merchant_step = "login_or_register"

if st.session_state.merchant_step == "login_or_register":
    st.subheader("👋 أهلاً بك في بوابة تجار الكرك")
    choice = st.radio(
        "اختر العملية:",
        ["تسجيل دخول متجر معتمد مسبقاً", "تسجيل متجر جديد لأول مرة"],
    )

    if choice == "تسجيل دخول متجر معتمد مسبقاً":
        try:
            res = sb.table("merchants").select("*").eq("status", "معتمد").execute()
            all_m = res.data if res.data else []
        except Exception:
            all_m = []

        if not all_m:
            st.info("لا توجد أي متاجر معتمدة حالياً. يرجى اختيار 'تسجيل متجر جديد لأول مرة'.")
        else:
            m_options = {f"{m.get('name')} ({m.get('category')} - هاتف: {m.get('phone')})": m for m in all_m}
            selected_key = st.selectbox("اختر المتجر:", list(m_options.keys()))
            quick_phone_check = st.text_input("أو أدخل رقم هاتفك للتحقق المباشر والدخول:", "")

            col_in1, col_in2 = st.columns(2)
            with col_in1:
                if st.button("دخول لوحة التحكم بالمتجر المختار"):
                    selected_store = m_options[selected_key]
                    st.session_state.logged_merchant_id = selected_store.get("id")
                    st.session_state.logged_merchant_data = selected_store
                    st.session_state.merchant_step = "dashboard"
                    st.rerun()
            with col_in2:
                if st.button("تحقق ودخول برقم الهاتف المدخل"):
                    if quick_phone_check:
                        found = next((m for m in all_m if str(m.get("phone")) == str(quick_phone_check).strip()), None)
                        if found:
                            st.session_state.logged_merchant_id = found.get("id")
                            st.session_state.logged_merchant_data = found
                            st.session_state.merchant_step = "dashboard"
                            st.success("تم التعرف على المتجر بنجاح! جاري الدخول...")
                            st.rerun()
                        else:
                            st.warning("⚠️ رقم الهاتف غير معتمد أو غير مسجل بعد لدى الإدارة.")
                    else:
                        st.error("الرجاء إدخال رقم الهاتف أولاً.")

    else:
        with st.form("new_merchant_reg"):
            st.subheader("📝 نموذج انضمام متجر جديد وإرسال الطلب للإدارة")
            reg_name = st.text_input("اسم المتجر الكامل")
            reg_cat = st.selectbox(
                "القسم الرئيسي",
                [
                    "مطاعم",
                    "حلويات",
                    "ماركت",
                    "محامص ومكسرات",
                    "خضروات وفواكه",
                    "لحوم",
                    "صيدليات ومستلزمات طبيه",
                ],
            )
            reg_phone = st.text_input("رقم هاتف المتجر (المعرف الأساسي للدخول)")
            reg_address_detail = st.text_input("العنوان التفصيلي (المدينة، الحي، الشارع)", "الكرك - المرج")
            reg_m_img = st.file_uploader("صورة المتجر الرئيسية (شعار أو واجهة)", type=["jpg", "png", "jpeg"])

            reg_geo_link = st.text_input(
                "رابط موقع المتجر على خرائط جوجل (Google Maps URL)",
                value="https://maps.app.goo.gl/KarakStore",
            )

            accept_terms = st.checkbox("أوافق على كافة الشروط والأحكام وعمولة التشغيل (10%)")
            submit_reg = st.form_submit_button("إرسال طلب الانضمام وتسجيل المتجر للإدارة")

            if submit_reg:
                if not reg_name or not reg_phone:
                    st.error("الرجاء إدخال اسم المتجر ورقم الهاتف على الأقل.")
                elif not accept_terms:
                    st.error("يجب الموافقة على الشروط والأحكام للمتابعة.")
                else:
                    try:
                        img_b64 = process_uploaded_image(reg_m_img)
                        full_loc_data = f"{reg_address_detail} | خريطة: {reg_geo_link}"
                        
                        sb.table("merchants").insert({
                            "name": reg_name,
                            "category": reg_cat,
                            "phone": reg_phone,
                            "location": full_loc_data,
                            "status": "قيد المراجعة",
                            "image_data": img_b64
                        }).execute()

                        st.success("🎉 تم إرسال طلب انضمام متجرك بنجاح إلى الإدارة! سيتم مراجعته واعتماده قريباً.")
                    except Exception as e:
                        st.error(f"عطل أو رقم الهاتف مستخدم مسبقاً: {e}")

elif st.session_state.merchant_step == "dashboard":
    m_id = st.session_state.get("logged_merchant_id")
    try:
        res = sb.table("merchants").select("*").eq("id", m_id).execute()
        m_data = res.data[0] if res.data else st.session_state.get("logged_merchant_data", {})
    except Exception:
        m_data = st.session_state.get("logged_merchant_data", {})

    m_name = m_data.get("name", "متجر")
    m_cat = m_data.get("category", "")
    m_loc = m_data.get("location", "")
    m_phone = m_data.get("phone", "")
    m_img = m_data.get("image_data", "")

    col_logo, col_info = st.columns([1, 3])
    with col_logo:
        if m_img:
            st.image(m_img, width=120)
        else:
            st.write("🏬 **[لا توجد صورة للمتجر]**")
    with col_info:
        st.success(f"✅ لوحة تحكم المتجر: {m_name} | التصنيف: {m_cat}")
        st.info(f"📍 الموقع: {m_loc} | 📞 الهاتف: {m_phone}")

    if st.button("⬅️ تسجيل الخروج / تبديل المتجر"):
        for key in ["logged_merchant_id", "logged_merchant_data"]:
            if key in st.session_state:
                del st.session_state[key]
        st.session_state.merchant_step = "login_or_register"
        st.rerun()

    # فحص الطلبات الواردة الجديدة
    try:
        ord_res = sb.table("orders").select("id, order_details, order_status").execute().data or []
        pending_orders_count = sum(
            1 for o in ord_res 
            if o.get("order_status") == "قيد التجهيز" and m_name in str(o.get("order_details", ""))
        )
    except Exception:
        pending_orders_count = 0

    if pending_orders_count > 0:
        st.markdown(
            f"""
            <div class="bell-alert">
                🔔 تنبيه هام: يوجد ({pending_orders_count}) طلب جديد موجه إلى متجرك بحاجة لتجهيزه الفوري!
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("---")

    tab1, tab2, tab3, tab4 = st.tabs([
        "📋 إدارة الأصناف والقوائم",
        "🏷️️ العروض والتخفيضات",
        "📦 طلبات المتجر الواردة ومتابعة السائقين",
        "⚙️ تعديل معلومات وصورة المتجر",
    ])

    with tab1:
        st.subheader(f"📋 إضافة الأصناف والمنتجات لمتجر: {m_name}")
        with st.form("merchant_add_prod"):
            p_name = st.text_input("اسم الصنف (مثال: منسف لحم، صحن حمص، ساندويش)")
            c1, c2 = st.columns(2)
            with c1:
                p_qty = st.text_input("الكمية المتوفرة", value="1")
            with c2:
                p_unit = st.selectbox(
                    "الوحدة",
                    ["وجبة", "حبة", "عدد", "صحن", "كيلو", "غرام", "باكيت", "عبوة", "لتر", "قطعة", "دستة"],
                )

            p_price = st.number_input("السعر (دينار أردني)", min_value=0.1, value=1.0, step=0.25)
            p_img_file = st.file_uploader("رفع صورة الصنف", type=["jpg", "png", "jpeg"])

            submit_p = st.form_submit_button("إضافة الصنف للقائمة")
            if submit_p and p_name:
                try:
                    p_img_b64 = process_uploaded_image(p_img_file)
                    sb.table("products").insert({
                        "merchant_name": m_name,
                        "item_name": p_name,
                        "price": p_price,
                        "quantity": p_qty,
                        "unit": p_unit,
                        "image_path": p_img_b64
                    }).execute()
                    st.success(f"تم إضافة الصنف ({p_name}) بنجاح!")
                    st.rerun()
                except Exception as e:
                    st.error(f"خطأ أثناء إضافة الصنف: {e}")

        st.markdown("---")
        st.subheader("📋 قائمة الأصناف الحالية في متجرك:")
        try:
            prod_res = sb.table("products").select("*").eq("merchant_name", m_name).execute()
            prods = prod_res.data if prod_res.data else []
        except Exception:
            prods = []

        if prods:
            for p in prods:
                p_id = p.get("id")
                it_name = p.get("item_name")
                it_qty = p.get("quantity", "1")
                it_unit = p.get("unit", "حبة")
                it_price = p.get("price", 0.0)
                it_img = p.get("image_path", "")

                col_p_img, col_p_info, col_p_del = st.columns([1, 4, 1])
                with col_p_img:
                    if it_img:
                        st.image(it_img, width=80)
                    else:
                        st.write("📷 [لا توجد صورة]")
                with col_p_info:
                    st.markdown(
                        f"""
                        <div class="item-card">
                            <p style="margin: 0; font-size: 18px; font-weight: bold; color: #000000;">🍽️ {it_name}</p>
                            <p style="margin: 5px 0 0 0; color: #333333;">الكمية: <b>{it_qty} {it_unit}</b> | السعر: <b>{it_price} د.أ</b></p>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                with col_p_del:
                    if st.button("🗑️ حذف", key=f"del_item_{p_id}"):
                        sb.table("products").delete().eq("id", p_id).execute()
                        st.success("تم حذف الصنف بنجاح!")
                        st.rerun()
                st.markdown("---")
        else:
            st.info("لا توجد أصناف مضافة حالياً في متجرك.")

    with tab2:
        st.subheader("🏷️ إضافة عروض وخصومات خاصة بمتجرك")
        with st.form("merchant_offer_form"):
            off_title = st.text_input("عنوان العرض")
            off_desc = st.text_area("تفاصيل العرض والشروط")
            off_date = st.text_input("ساري لغاية تاريخ", "2026-12-31")

            sub_off = st.form_submit_button("نشر العرض")
            if sub_off and off_title:
                try:
                    sb.table("offers").insert({
                        "merchant_name": m_name,
                        "title": off_title,
                        "discount_details": off_desc,
                        "valid_until": off_date
                    }).execute()
                    st.success("تم نشر العرض بنجاح!")
                    st.rerun()
                except Exception as e:
                    st.error(f"خطأ أثناء نشر العرض: {e}")

    with tab3:
        st.subheader("📦 طلبات المتجر الواردة ومتابعة السائقين (خصم العمولة 10%)")
        try:
            all_orders = sb.table("orders").select("*").order("id", desc=True).execute().data or []
            merchant_orders = [o for o in all_orders if m_name in str(o.get("order_details", ""))]
        except Exception:
            merchant_orders = []

        if merchant_orders:
            for ord_item in merchant_orders:
                o_id = ord_item.get("id")
                o_tot = float(ord_item.get("total_amount") or 0)
                o_stat = ord_item.get("order_status", "قيد التجهيز")
                o_dname = ord_item.get("driver_name", "")
                o_time = ord_item.get("created_at", "")
                o_odet = ord_item.get("order_details", "")

                # حساب إجمالي أصناف المتجر وعمولته
                merchant_items_total = 0.0
                for line in o_odet.split("\n"):
                    if f"المتجر: {m_name}" in line:
                        match = re.search(r"\((\d+(\.\d+)?) د\.أ\)", line)
                        if match:
                            merchant_items_total += float(match.group(1))

                if merchant_items_total == 0.0:
                    merchant_items_total = max(0.0, o_tot - 1.75)

                commission_fee = merchant_items_total * 0.10
                net_merchant_amount = merchant_items_total - commission_fee

                driver_status_text = "في انتظار تعيين سائق وتوجهه للمتجر"
                if o_dname:
                    if o_stat == "تم التوصيل":
                        driver_status_text = f"✅ استلم الكابتن ({o_dname}) الطلب وتم تسليمه للزبون."
                    else:
                        driver_status_text = f"🛵 الكابتن ({o_dname}) يتابع الطلب حالياً."

                st.markdown(
                    f"""
                    <div class="merchant-card">
                        <h4>🛒 طلب رقم #{o_id}</h4>
                        <p><b>🕒 الوقت:</b> {o_time} | <b>📌 حالة التجهيز:</b> {o_stat}</p>
                        <p><b>🚚 حالة السائق:</b> <span style="color: #D84315; font-weight: bold;">{driver_status_text}</span></p>
                        <p><b>إجمالي أصناف متجرك:</b> {merchant_items_total:.2f} د.أ | <span style="color: #C62828;"><b>العمولة (10%):</b> {commission_fee:.2f} د.أ</span> | <b>الصافي:</b> {net_merchant_amount:.2f} د.أ</p>
                        <hr style="border: 0.5px solid #ddd;">
                        <pre style="background-color: #F9F9F9; padding: 10px; border-radius: 5px; color: #000000; border: 1px solid #ddd;">{o_odet}</pre>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                if o_stat == "قيد التجهيز":
                    if st.button(f"✨ تأكيد جاهزية الطلب رقم #{o_id}", key=f"ready_ord_{o_id}"):
                        sb.table("orders").update({"order_status": "جاهز للاستلام"}).eq("id", o_id).execute()
                        st.success("تم تحديث حالة الطلب بأنه جاهز للاستلام!")
                        st.rerun()
                st.markdown("---")
        else:
            st.info("لا توجد طلبات واردة لمتجرك حتى الآن.")

    with tab4:
        st.subheader("⚙️ تعديل بيانات ومعلومات وصورة المتجر")
        with st.form("edit_merchant_form"):
            edit_name = st.text_input("اسم المتجر", value=m_name)
            edit_cat = st.selectbox(
                "التصنيف الرئيسي",
                ["مطاعم", "حلويات", "ماركت", "محامص ومكسرات", "خضروات وفواكه", "لحوم", "صيدليات ومستلزمات طبيه"],
                index=["مطاعم", "حلويات", "ماركت", "محامص ومكسرات", "خضروات وفواكه", "لحوم", "صيدليات ومستلزمات طبيه"].index(m_cat) if m_cat in ["مطاعم", "حلويات", "ماركت", "محامص ومكسرات", "خضروات وفواكه", "لحوم", "صيدليات ومستلزمات طبيه"] else 0
            )
            edit_phone = st.text_input("رقم الهاتف", value=m_phone)
            edit_loc = st.text_input("العنوان ووصف الموقع", value=m_loc)

            st.markdown("### 📷 تحديث صورة المتجر الرئيسية")
            edit_img_file = st.file_uploader("اختر صورة جديدة للمتجر (JPG, PNG)", type=["jpg", "png", "jpeg"])

            submit_edit = st.form_submit_button("💾 حفظ وتحديث بيانات المتجر")
            if submit_edit:
                try:
                    new_img_b64 = process_uploaded_image(edit_img_file)
                    update_payload = {
                        "name": edit_name,
                        "category": edit_cat,
                        "phone": edit_phone,
                        "location": edit_loc
                    }
                    if new_img_b64:
                        update_payload["image_data"] = new_img_b64

                    sb.table("merchants").update(update_payload).eq("id", m_id).execute()
                    st.success("تم تحديث بيانات وصورة المتجر بنجاح!")
                    st.rerun()
                except Exception as e:
                    st.error(f"خطأ أثناء تحديث البيانات: {e}")
