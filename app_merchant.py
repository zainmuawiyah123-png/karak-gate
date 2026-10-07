import os
import re
import sqlite3
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Halago", page_icon="🔔", layout="wide"
)

st.markdown(
    """
    <style>
    /* إخفاء شريط القائمة العلوي وترويسة Streamlit بالكامل وأزرار النشر و GitHub Fork */
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
    .bell-alert span, .bell-alert div {
        color: white !important;
    }
    </style>
""",
    unsafe_allow_html=True,
)

UPLOAD_DIR = "uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)


def get_db():
    return sqlite3.connect("karak_gate.db", check_same_thread=False)


def init_merchant_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS merchants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            category TEXT,
            phone TEXT UNIQUE,
            location TEXT,
            status TEXT,
            image_path TEXT
        )
    """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS offers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            merchant_name TEXT,
            title TEXT,
            discount_details TEXT,
            valid_until TEXT
        )
    """
    )
    cursor.execute("PRAGMA table_info(products)")
    cols = [col[1] for col in cursor.fetchall()]
    if "quantity" not in cols:
        try:
            cursor.execute("ALTER TABLE products ADD COLUMN quantity TEXT")
        except Exception:
            pass  # العمود موجود مسبقاً، يتم تخطي الخطأ بسلاسة
    if "unit" not in cols:
        cursor.execute("ALTER TABLE products ADD COLUMN unit TEXT")
    if "image_path" not in cols:
        cursor.execute("ALTER TABLE products ADD COLUMN image_path TEXT")

    cursor.execute("PRAGMA table_info(merchants)")
    m_cols = [col[1] for col in cursor.fetchall()]
    if "image_path" not in m_cols:
        cursor.execute("ALTER TABLE merchants ADD COLUMN image_path TEXT")

    conn.commit()
    conn.close()


init_merchant_db()

st.title("🏬 بوابة المتاجر الشاملة - Halago")

if "merchant_step" not in st.session_state:
    st.session_state.merchant_step = "login_or_register"

if st.session_state.merchant_step == "login_or_register":
    st.subheader("👋 أهلاً بك في بوابة تجار Halago")
    choice = st.radio(
        "اختر العملية:",
        ["تسجيل دخول متجر مسجل مسبقاً", "تسجيل متجر جديد لأول مرة"],
    )

    if choice == "تسجيل دخول متجر مسجل مسبقاً":
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, category, location, status, phone FROM merchants")
        all_m = cursor.fetchall()
        conn.close()

        if not all_m:
            st.info(
                "لا توجد أي متاجر مسجلة حالياً. يرجى اختيار 'تسجيل متجر جديد لأول مرة'."
            )
        else:
            m_options = {f"{m[1]} ({m[2]} - هاتف: {m[5]})": m for m in all_m}
            selected_key = st.selectbox(
                "اختر المتجر أو ابحث برقم هاتفك:", list(m_options.keys())
            )

            quick_phone_check = st.text_input(
                "أو أدخل رقم هاتفك للتحقق المباشر والدخول:", ""
            )

            col_in1, col_in2 = st.columns(2)
            with col_in1:
                if st.button("دخول لوحة التحكم للمتجر المختصر"):
                    st.session_state.logged_merchant_id = m_options[selected_key][0]
                    st.session_state.logged_merchant = m_options[selected_key][1:]
                    st.session_state.merchant_step = "dashboard"
                    st.rerun()
            with col_in2:
                if st.button("تحقق ودخول برقم الهاتف المدخل"):
                    if quick_phone_check:
                        conn = get_db()
                        cur_q = conn.cursor()
                        cur_q.execute(
                            "SELECT id, name, category, location, status, phone FROM merchants WHERE phone = ?",
                            (quick_phone_check,),
                        )
                        found_m = cur_q.fetchone()
                        conn.close()

                        if found_m:
                            st.session_state.logged_merchant_id = found_m[0]
                            st.session_state.logged_merchant = found_m[1:]
                            st.session_state.merchant_step = "dashboard"
                            st.success("تم التعرف على المتجر بنجاح! جاري الدخول...")
                            st.rerun()
                        else:
                            st.warning(
                                "⚠️ رقم الهاتف غير مسجل مسبقاً لدى الإدارة. يرجى الانتقال لخيار"
                                " 'تسجيل متجر جديد لأول مرة' أدناه."
                            )
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
            reg_phone = st.text_input("رقم هاتف المتجر (سيتم اعتماده لرقم الدخول)")
            reg_address_detail = st.text_input(
                "العنوان التفصيلي (المدينة، الحي، الشارع)", "الكرك - المرج"
            )
            reg_m_img = st.file_uploader(
                "صورة المتجر الرئيسية (شعار أو واجهة المتجر)", type=["jpg", "png", "jpeg"]
            )

            st.markdown("### 🗺️ خريطة جوجل التفاعلية للموقع")
            map_html = """
                <iframe width="100%" height="220" frameborder="0" scrolling="no" marginheight="0" marginwidth="0" 
                    src="https://maps.google.com/maps?q=Al-Karak,+Jordan&t=&z=13&ie=UTF8&iwloc=&output=embed">
                </iframe>
                """
            st.components.v1.html(map_html, height=230)

            reg_geo_link = st.text_input(
                "رابط موقع المتجر على خرائط جوجل أو الإحداثيات",
                value="https://maps.app.goo.gl/KarakStore",
            )

            st.markdown("---")
            st.markdown("### 📜 الشروط والأحكام والسياسات الخاصة بـ Halago")
            st.markdown(
                """
                1. الالتزام بجودة المنتجات والأسعار المعتمدة.
                2. خصم نسبة 10% كعمولة تشغيلية لHalago من إجمالي أصناف المتجر فقط.
                3. تجهيز الطلبات الواردة فور وصول إشعار الجرس الفوري.
                """
            )
            accept_terms = st.checkbox(
                "أوافق على كافة الشروط والأحكام وسياسة التشغيل"
            )

            submit_reg = st.form_submit_button(
                "إرسال طلب الانضمام وتسجيل المتجر للإدارة"
            )
            if submit_reg:
                if not reg_name or not reg_phone:
                    st.error("الرجاء إدخال اسم المتجر ورقم الهاتف على الأقل.")
                elif not accept_terms:
                    st.error("يجب الموافقة على الشروط والأحكام للمتابعة.")
                else:
                    try:
                        m_img_path = ""
                        if reg_m_img is not None:
                            m_img_path = os.path.join(UPLOAD_DIR, reg_m_img.name)
                            with open(m_img_path, "wb") as f:
                                f.write(reg_m_img.getbuffer())

                        conn = get_db()
                        cursor = conn.cursor()
                        full_loc_data = f"{reg_address_detail} | خريطة: {reg_geo_link}"
                        cursor.execute(
                            """
                                INSERT INTO merchants (name, category, phone, location, status, image_path)
                                VALUES (?, ?, ?, ?, ?, ?)
                            """,
                            (reg_name, reg_cat, reg_phone, full_loc_data, "معتمد", m_img_path),
                        )
                        conn.commit()
                        conn.close()
                        st.success(
                            "🎉 تم تسجيل متجرك بنجاح وتم اعتماده في النظام! يمكنك الآن تسجيل"
                            " الدخول برقم هاتفك."
                        )
                    except Exception as e:
                        st.error(f"عطل أو رقم الهاتف مستخدم مسبقاً: {e}")

elif st.session_state.merchant_step == "dashboard":
    conn_db = get_db()
    cur_db = conn_db.cursor()
    cur_db.execute(
        "SELECT name, category, location, status, phone, image_path FROM merchants WHERE"
        " id = ?",
        (st.session_state.logged_merchant_id,),
    )
    refreshed_m = cur_db.fetchone()
    conn_db.close()

    if refreshed_m:
        m_name, m_cat, m_loc, m_status, m_phone, m_img_path = refreshed_m
    else:
        m_name, m_cat, m_loc, m_status, m_phone = st.session_state.logged_merchant
        m_img_path = ""

    col_logo, col_info = st.columns([1, 3])
    with col_logo:
        if m_img_path and os.path.exists(m_img_path):
            st.image(m_img_path, width=
