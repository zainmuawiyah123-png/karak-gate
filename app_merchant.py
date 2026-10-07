import os
import re
import sqlite3
import pandas as pd
import streamlit as st

# ============================================================
# إعداد الصفحة
# ============================================================

st.set_page_config(
    page_title="Halago",
    page_icon="🔔",
    layout="wide"
)

# ============================================================
# CSS
# ============================================================

st.markdown(
    """
    <style>

    /* إخفاء عناصر Streamlit */
    #MainMenu {
        visibility: hidden;
    }

    .stDeployButton {
        display: none;
    }

    header {
        visibility: hidden;
    }

    footer {
        visibility: hidden;
    }

    /* الخلفية الرئيسية */
    .stApp {
        background-color: #FF5722 !important;
        color: #000000 !important;
    }

    /* النصوص */
    h1, h2, h3, h4, h5, h6, p, label, span {
        color: #000000 !important;
    }

    /* الأزرار */
    .stButton > button {
        border-radius: 8px;
        font-weight: bold;
        border: none;
        background-color: #FFFFFF !important;
        color: #FF5722 !important;
        min-height: 42px;
    }

    .stButton > button:hover {
        background-color: #FFF3E0 !important;
        color: #E64A19 !important;
    }

    /* بطاقة المتجر */
    .merchant-card {
        background-color: #FFFFFF;
        padding: 20px;
        border-radius: 12px;
        margin-bottom: 15px;
        border: 2px solid #E0E0E0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }

    .merchant-card h4,
    .merchant-card p,
    .merchant-card span {
        color: #000000 !important;
    }

    /* بطاقة الصنف */
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

    /* حركة التنبيه */
    @keyframes pulse {
        0% {
            transform: scale(1);
        }

        50% {
            transform: scale(1.05);
        }

        100% {
            transform: scale(1);
        }
    }

    /* تنبيه */
    .bell-alert {
        background-color: #B71C1C;
        color: white !important;
        padding: 15px;
        border-radius: 10px;
        text-align: center;
        font-weight: bold;
        font-size: 20px;
        animation: pulse 1.5s infinite;
        margin-bottom: 20px;
    }

    .bell-alert p,
    .bell-alert span,
    .bell-alert h3 {
        color: white !important;
    }

    /* عنوان التطبيق */
    .app-title {
        background-color: #FFFFFF;
        padding: 15px;
        border-radius: 12px;
        text-align: center;
        margin-bottom: 20px;
    }

    .app-title h1 {
        color: #FF5722 !important;
        margin: 0;
    }

    /* صندوق المعلومات */
    .info-box {
        background-color: #FFFFFF;
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 15px;
        border: 1px solid #E0E0E0;
    }

    /* الحقول */
    input,
    textarea,
    select {
        border-radius: 8px !important;
    }

    </style>
    """,
    unsafe_allow_html=True
)

# ============================================================
# عنوان التطبيق
# ============================================================

st.markdown(
    """
    <div class="app-title">
        <h1>🔔 Halago</h1>
        <p>Merchant Management</p>
    </div>
    """,
    unsafe_allow_html=True
)

# ============================================================
# قاعدة البيانات
# ============================================================

DB_FILE = "halago.db"


def get_connection():
    return sqlite3.connect(DB_FILE)


# ============================================================
# إنشاء قاعدة البيانات
# ============================================================

def init_database():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS merchants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT,
            phone TEXT,
            address TEXT,
            image TEXT,
            status TEXT DEFAULT 'معتمد'
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            merchant_id INTEGER,
            name TEXT NOT NULL,
            category TEXT,
            price REAL DEFAULT 0,
            image TEXT,
            description TEXT,
            available INTEGER DEFAULT 1
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            merchant_id INTEGER,
            customer_name TEXT,
            customer_phone TEXT,
            address TEXT,
            total REAL DEFAULT 0,
            status TEXT DEFAULT 'جديد',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    conn.commit()
    conn.close()


init_database()

# ============================================================
# وظائف قاعدة البيانات
# ============================================================

def get_merchants():

    conn = get_connection()

    try:
        df = pd.read_sql_query(
            """
            SELECT *
            FROM merchants
            ORDER BY id DESC
            """,
            conn
        )
    except Exception:
        df = pd.DataFrame()

    conn.close()

    return df


def get_products(merchant_id=None):

    conn = get_connection()

    try:

        if merchant_id is None:

            df = pd.read_sql_query(
                """
                SELECT *
                FROM products
                ORDER BY id DESC
                """,
                conn
            )

        else:

            df = pd.read_sql_query(
                """
                SELECT *
                FROM products
                WHERE merchant_id = ?
                ORDER BY id DESC
                """,
                conn,
                params=(merchant_id,)
            )

    except Exception:
        df = pd.DataFrame()

    conn.close()

    return df


def get_orders():

    conn = get_connection()

    try:

        df = pd.read_sql_query(
            """
            SELECT *
            FROM orders
            ORDER BY id DESC
            """,
            conn
        )

    except Exception:
        df = pd.DataFrame()

    conn.close()

    return df


# ============================================================
# Session State
# ============================================================

if "merchant_id" not in st.session_state:
    st.session_state.merchant_id = None

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False


# ============================================================
# القائمة الجانبية
# ============================================================

st.sidebar.title("🔔 Halago")

page = st.sidebar.radio(
    "القائمة",
    [
        "🏪 المتجر",
        "📦 المنتجات",
        "🛒 الطلبات",
        "➕ إضافة منتج",
        "⚙️ الإعدادات"
    ]
)

# ============================================================
# صفحة المتجر
# ============================================================

if page == "🏪 المتجر":

    st.header("🏪 إدارة المتجر")

    merchants = get_merchants()

    if merchants.empty:

        st.info("لا يوجد متجر مسجل حالياً.")

        with st.form("merchant_form"):

            name = st.text_input("اسم المتجر")

            category = st.text_input(
                "التصنيف",
                placeholder="مطاعم / حلويات / ماركت..."
            )

            phone = st.text_input("رقم الهاتف")

            address = st.text_input("العنوان")

            image = st.text_input(
                "رابط صورة المتجر",
                placeholder="https://..."
            )

            submit = st.form_submit_button(
                "➕ إنشاء المتجر"
            )

            if submit:

                if not name.strip():

                    st.error("يرجى إدخال اسم المتجر.")

                else:

                    conn = get_connection()
                    cursor = conn.cursor()

                    cursor.execute(
                        """
                        INSERT INTO merchants
                        (name, category, phone, address, image, status)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            name.strip(),
                            category.strip(),
                            phone.strip(),
                            address.strip(),
                            image.strip(),
                            "معتمد"
                        )
                    )

                    conn.commit()
                    conn.close()

                    st.success("تم إنشاء المتجر بنجاح.")
                    st.rerun()

    else:

        for _, merchant in merchants.iterrows():

            st.markdown(
                f"""
                <div class="merchant-card">

                    <h4>🏪 {merchant.get("name", "")}</h4>

                    <p>
                    <b>التصنيف:</b>
                    {merchant.get("category", "")}
                    </p>

                    <p>
                    <b>الهاتف:</b>
                    {merchant.get("phone", "")}
                    </p>

                    <p>
                    <b>العنوان:</b>
                    {merchant.get("address", "")}
                    </p>

                    <p>
                    <b>الحالة:</b>
                    {merchant.get("status", "معتمد")}
                    </p>

                </div>
                """,
                unsafe_allow_html=True
            )

# ============================================================
# صفحة المنتجات
# ============================================================

elif page == "📦 المنتجات":

    st.header("📦 منتجات المتجر")

    merchants = get_merchants()

    if merchants.empty:

        st.warning("يجب إنشاء متجر أولاً.")

    else:

        merchant_options = {}

        for _, row in merchants.iterrows():

            merchant_options[
                f'{row["name"]} - {row["category"]}'
            ] = int(row["id"])

        selected = st.selectbox(
            "اختر المتجر",
            list(merchant_options.keys())
        )

        merchant_id = merchant_options[selected]

        products = get_products(merchant_id)

        if products.empty:

            st.info("لا توجد منتجات لهذا المتجر.")

        else:

            for _, product in products.iterrows():

                available = (
                    "متوفر"
                    if int(product.get("available", 1)) == 1
                    else "غير متوفر"
                )

                st.markdown(
                    f"""
                    <div class="item-card">

                        <h4>🍔 {product.get("name", "")}</h4>

                        <p>
                        <b>التصنيف:</b>
                        {product.get("category", "")}
                        </p>

                        <p>
                        <b>السعر:</b>
                        {float(product.get("price", 0)):.2f} JOD
                        </p>

                        <p>
                        <b>الحالة:</b>
                        {available}
                        </p>

                        <p>
                        {product.get("description", "")}
                        </p>

                    </div>
                    """,
                    unsafe_allow_html=True
                )

# ============================================================
# إضافة منتج
# ============================================================

elif page == "➕ إضافة منتج":

    st.header("➕ إضافة منتج جديد")

    merchants = get_merchants()

    if merchants.empty:

        st.warning("يجب إنشاء متجر أولاً.")

    else:

        merchant_options = {}

        for _, row in merchants.iterrows():

            merchant_options[
                f'{row["name"]} - {row["category"]}'
            ] = int(row["id"])

        selected = st.selectbox(
            "اختر المتجر",
            list(merchant_options.keys())
        )

        merchant_id = merchant_options[selected]

        with st.form("add_product_form"):

            product_name = st.text_input(
                "اسم المنتج"
            )

            category = st.text_input(
                "تصنيف المنتج"
            )

            price = st.number_input(
                "السعر بالدينار",
                min_value=0.0,
                step=0.10
            )

            image = st.text_input(
                "رابط صورة المنتج"
            )

            description = st.text_area(
                "وصف المنتج"
            )

            available = st.checkbox(
                "المنتج متوفر",
                value=True
            )

            submit = st.form_submit_button(
                "💾 حفظ المنتج"
            )

            if submit:

                if not product_name.strip():

                    st.error(
                        "يرجى إدخال اسم المنتج."
                    )

                else:

                    conn = get_connection()
                    cursor = conn.cursor()

                    cursor.execute(
                        """
                        INSERT INTO products
                        (
                            merchant_id,
                            name,
                            category,
                            price,
                            image,
                            description,
                            available
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            merchant_id,
                            product_name.strip(),
                            category.strip(),
                            price,
                            image.strip(),
                            description.strip(),
                            1 if available else 0
                        )
                    )

                    conn.commit()
                    conn.close()

                    st.success(
                        "تمت إضافة المنتج بنجاح."
                    )

# ============================================================
# الطلبات
# ============================================================

elif page == "🛒 الطلبات":

    st.header("🛒 الطلبات")

    orders = get_orders()

    if orders.empty:

        st.info("لا توجد طلبات حالياً.")

    else:

        st.dataframe(
            orders,
            use_container_width=True,
            hide_index=True
        )

# ============================================================
# الإعدادات
# ============================================================

elif page == "⚙️ الإعدادات":

    st.header("⚙️ الإعدادات")

    st.markdown(
        """
        <div class="info-box">

        <h4>🔔 Halago Merchant</h4>

        <p>
        لوحة إدارة المتجر والمنتجات والطلبات.
        </p>

        <p>
        يمكن تطوير هذه الصفحة لاحقاً لربطها مباشرة
        مع قاعدة بيانات Supabase الخاصة بتطبيق
        <b>Halago</b>.
        </p>

        </div>
        """,
        unsafe_allow_html=True
    )

    if st.button("🔄 تحديث البيانات"):

        st.rerun()

# ============================================================
# نهاية البرنامج
# ============================================================
