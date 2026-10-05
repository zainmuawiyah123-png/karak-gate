import os
import sqlite3
import pandas as pd
import urllib.parse
import streamlit as st

st.set_page_config(
    page_title="بوابة السائقين - Karak Gate", page_icon="🛵", layout="wide"
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
    h1, h2, h3, h4, h5, h6, p, label, span, div {
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
    .driver-card {
        background-color: #FFFFFF;
        padding: 20px;
        border-radius: 12px;
        margin-bottom: 15px;
        border: 2px solid #E0E0E0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .driver-card h4, .driver-card p, .driver-card span {
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


def get_db():
    return sqlite3.connect("karak_gate.db", check_same_thread=False)


def init_driver_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS drivers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            phone TEXT UNIQUE,
            vehicle_type TEXT,
            status TEXT
        )
    """
    )

    try:
        cursor.execute("ALTER TABLE orders ADD COLUMN picked_up INTEGER DEFAULT 0")
        conn.commit()
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("ALTER TABLE orders ADD COLUMN cash_collected INTEGER DEFAULT 0")
        conn.commit()
    except sqlite3.OperationalError:
        pass

    conn.close()


init_driver_db()

st.title("🛵 بوابة السائقين ومناديب التوصيل - Karak Gate")

if "driver_step" not in st.session_state:
    st.session_state.driver_step = "login_or_register"

if st.session_state.driver_step == "login_or_register":
    st.subheader("👋 أهلاً بك في بوابة السائقين والكابتن")
    choice = st.radio(
        "اختر العملية:",
        ["تسجيل دخول سائق مسجل مسبقاً", "تسجيل سائق جديد لأول مرة"],
    )

    if choice == "تسجيل دخول سائق مسجل مسبقاً":
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, vehicle_type, phone FROM drivers")
        all_d = cursor.fetchall()
        conn.close()

        if not all_d:
            st.info(
                "لا توجد أي سائقين مسجلين حالياً. يرجى اختيار 'تسجيل سائق جديد لأول مرة'."
            )
        else:
            d_options = {f"{d[1]} ({d[2]} - هاتف: {d[3]})": d for d in all_d}
            selected_key = st.selectbox(
                "اختر اسمك أو ابحث برقم هاتفك:", list(d_options.keys())
            )

            quick_phone = st.text_input(
                "أو أدخل رقم هاتفك للتحقق المباشر والدخول:", ""
            )

            col_d1, col_d2 = st.columns(2)
            with col_d1:
                if st.button("دخول لوحة السائق المختارة"):
                    st.session_state.logged_driver_id = d_options[selected_key][0]
                    st.session_state.logged_driver = d_options[selected_key][1:]
                    st.session_state.driver_step = "dashboard"
                    st.rerun()
            with col_d2:
                if st.button("تحقق ودخول برقم الهاتف"):
                    if quick_phone:
                        conn = get_db()
                        cur_q = conn.cursor()
                        cur_q.execute(
                            "SELECT id, name, vehicle_type, phone FROM drivers WHERE phone = ?",
                            (quick_phone,),
                        )
                        found_d = cur_q.fetchone()
                        conn.close()

                        if found_d:
                            st.session_state.logged_driver_id = found_d[0]
                            st.session_state.logged_driver = found_d[1:]
                            st.session_state.driver_step = "dashboard"
                            st.success("تم التعرف على السائق بنجاح! جاري الدخول...")
                            st.rerun()
                        else:
                            st.warning(
                                "⚠️ رقم الهاتف غير مسجل مسبقاً. يرجى التسجيل كسايق جديد."
                            )
                    else:
                        st.error("الرجاء إدخال رقم الهاتف أولاً.")

    else:
        with st.form("new_driver_reg"):
            st.subheader("📝 نموذج انضمام سائق جديد للإدارة")
            d_name = st.text_input("الاسم الكامل للسائق")
            d_phone = st.text_input("رقم الهاتف المحمول (للتواصل ودخول البوابة)")
            d_vehicle = st.selectbox(
                "نوع وسيلة النقل",
                ["دراجة نارية (موتوسيكل)", "سيارة خاصة", "سكوتر", "سرفيس/بايك"],
            )

            submit_d_reg = st.form_submit_button("إرسال طلب الانضمام كسايق")
            if submit_d_reg:
                if not d_name or not d_phone:
                    st.error("الرجاء إدخال الاسم ورقم الهاتف.")
                else:
                    try:
                        conn = get_db()
                        cursor = conn.cursor()
                        cursor.execute(
                            """
                            INSERT INTO drivers (name, phone, vehicle_type, status)
                            VALUES (?, ?, ?, ?)
                        """,
                            (d_name, d_phone, d_vehicle, "متاح"),
                        )
                        conn.commit()
                        conn.close()
                        st.success(
                            "🎉 تم تسجيلك بنجاح! يمكنك الآن تسجيل الدخول برقم هاتفك."
                        )
                    except Exception as e:
                        st.error(f"عطل أو رقم الهاتف مستخدم مسبقاً: {e}")

elif st.session_state.driver_step == "dashboard":
    conn_db = get_db()
    cur_db = conn_db.cursor()
    cur_db.execute(
        "SELECT name, vehicle_type, phone, status FROM drivers WHERE id = ?",
        (st.session_state.logged_driver_id,),
    )
    refreshed_d = cur_db.fetchone()
    conn_db.close()

    if refreshed_d:
        d_name, d_vehicle, d_phone, d_status = refreshed_d
    else:
        d_name, d_vehicle, d_phone = st.session_state.logged_driver
        d_status = "متاح"

    st.success(
        f"✅ لوحة تحكم السائق: الكابتن {d_name} | الوسيلة: {d_vehicle} | الهاتف: {d_phone}"
    )

    if st.button("⬅ تسجيل الخروج / تبديل الحساب"):
        if "logged_driver" in st.session_state:
            del st.session_state.logged_driver
        if "logged_driver_id" in st.session_state:
            del st.session_state.logged_driver_id
        st.session_state.driver_step = "login_or_register"
        st.rerun()

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, customer_name, customer_phone, customer_address, order_details, total_amount, payment_method, order_status, driver_name, lat, lng, created_at, picked_up, cash_collected FROM orders WHERE driver_name = ? OR driver_name = '' ORDER BY id DESC",
        (d_name,),
    )
    assigned_orders = cursor.fetchall()

    my_orders = [o for o in assigned_orders if o[8] == d_name]

    if my_orders:
        st.markdown(
            f"""
            <div class="bell-alert">
                🔔 تنبيه هام: يوجد لديك ({len(my_orders)}) طلب مسند من الإدارة بحاجة للتوصيل الفوري!
            </div>
        """,
            unsafe_allow_html=True,
        )

        sound_html = """
        <script>
        function playBell() {
            const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            const oscillator = audioCtx.createOscillator();
            const gainNode = audioCtx.createGain();
            oscillator.type = 'sine';
            oscillator.frequency.setValueAtTime(660, audioCtx.currentTime);
            gainNode.gain.setValueAtTime(0.3, audioCtx.currentTime);
            oscillator.connect(gainNode);
            gainNode.connect(audioCtx.destination);
            oscillator.start();
            oscillator.stop(audioCtx.currentTime + 0.4);
        }
        playBell();
        </script>
        """
        st.components.v1.html(sound_html, height=0)

    st.markdown("---")
    st.subheader("📦 الطلبات المتاحة والمسندة إليك:")

    if assigned_orders:
        for ord_item in assigned_orders:
            (
                o_id,
                o_cname,
                o_cphone,
                o_caddr,
                o_odet,
                o_tot,
                o_pay,
                o_ostat,
                o_dname,
                o_lat,
                o_lng,
                o_time,
                o_picked,
                o_cash,
            ) = ord_item

            store_name = "المتجر المعني"
            if "المتجر: " in o_odet:
                try:
                    parts = o_odet.split("المتجر: ")
                    if len(parts) > 1:
                        store_name = parts[1].split("]")[0].strip()
                except:
                    pass

            cursor.execute(
                "SELECT location FROM merchants WHERE name = ?", (store_name,)
            )
            store_row = cursor.fetchone()
            store_loc = store_row[0] if store_row else "الكرك - المرج"

            st.markdown(
                f"""
                <div class="driver-card">
                    <h4>🛒 طلب رقم #{o_id}</h4>
                    <p><b>🕒 وقت الطلب:</b> {o_time} | <b>📌 حالة الطلب:</b> {o_ostat} | <b>💳 طريقة الدفع:</b> {o_pay}</p>
                    <p><b>المتجر المطلوب منه:</b> {store_name}</p>
                    <hr style="border: 0.5px solid #ccc;">
                    <pre style="background-color: #F9F9F9; padding: 10px; border-radius: 5px; color: #000000; border: 1px solid #ddd;">{o_odet}</pre>
                    <p><b>المبلغ الإجمالي المطلوب تحصيله:</b> {o_tot} دينار</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            if o_picked == 0:
                st.markdown(
                    "### 🗺️ المرحلة الأولى: التوجه إلى المتجر لاستلام الطلب"
                )
                st.info(f"عنوان وموقع المتجر: {store_loc}")
                store_map_url = "https://maps.google.com/maps?q=Al-Karak,+Jordan&t=&z=15&ie=UTF8&iwloc=&output=embed"
                st.markdown(
                    f"""
                    <div style="border-radius: 10px; overflow: hidden; border: 2px solid white; margin-bottom: 15px;">
                        <iframe width="100%" height="220" frameborder="0" scrolling="no" src="{store_map_url}"></iframe>
                    </div>
                """,
                    unsafe_allow_html=True,
                )

                col_b1, col_b2 = st.columns(2)
                with col_b1:
                    if not o_dname or o_dname == "":
                        if st.button("🙋‍♂️ استلام مهمة التوصيل", key=f"take_ord_{o_id}"):
                            cursor.execute(
                                "UPDATE orders SET driver_name = ?, order_status = 'جاري التوصيل' WHERE id = ?",
                                (d_name, o_id),
                            )
                            conn.commit()
                            st.success("تم استلام المهمة بنجاح!")
                            st.rerun()
                with col_b2:
                    if st.button(
                        "✅ تم استلام الطلب من المتجر (الانتقال للمرحلة الثانية)",
                        key=f"pickup_ord_{o_id}",
                    ):
                        cursor.execute(
                            "UPDATE orders SET driver_name = ?, picked_up = 1, order_status = 'جاري التوصيل' WHERE id = ?",
                            (d_name, o_id),
                        )
                        conn.commit()
                        st.success("تم تأكيد الاستلام من المتجر وانتقلت للمرحلة الثانية!")
                        st.rerun()
            else:
                st.markdown(
                    "### 📍 المرحلة الثانية: التوصيل إلى الزبون (الخصوصية والاتصال والموقع)"
                )
                st.markdown(
                    f"""
                <div style="background-color: #FFF3E0; padding: 15px; border-radius: 10px; margin-bottom: 15px; border: 1px solid #FF5722;">
                    <p style="font-size: 18px; color: #D84315; margin-bottom: 5px;"><b>📞 رقم هاتف الزبون:</b> {o_cphone} <span style="font-size: 14px; color: #333;">(بدون اسم لحفظ الخصوصية)</span></p>
                    <p style="font-size: 16px; margin-bottom: 0; color: #000000;"><b>📍 العنوان العادي المسجل:</b> {o_caddr}</p>
                </div>
                """,
                    unsafe_allow_html=True,
                )

                cust_map_url = f"https://maps.google.com/maps?q={o_lat},{o_lng}&t=&z=15&ie=UTF8&iwloc=&output=embed"
                st.markdown(
                    f"""
                    <div style="border-radius: 10px; overflow: hidden; border: 2px solid white; margin-bottom: 15px;">
                        <iframe width="100%" height="250" frameborder="0" scrolling="no" src="{cust_map_url}"></iframe>
                    </div>
                """,
                    unsafe_allow_html=True,
                )

                col_sub1, col_sub2 = st.columns(2)

                if "نقداً" in o_pay:
                    with col_sub1:
                        if o_cash == 0:
                            if st.button(
                                "💵 تأكيد استلام المبلغ نقداً وتسليمه للإدارة",
                                key=f"cash_ord_{o_id}",
                            ):
                                cursor.execute(
                                    "UPDATE orders SET cash_collected = 1 WHERE id = ?",
                                    (o_id,),
                                )
                                conn.commit()
                                st.success(
                                    "تم تسجيل استلام المبلغ نقداً وإبلاغ الإدارة بنجاح!"
                                )
                                st.rerun()
                        else:
                            st.success("✅ تم تأكيد استلام المبلغ نقداً مسبقاً.")

                with col_sub2:
                    if st.button(
                        "🏁 تأكيد تسليم الطلب للزبون وإغلاق الطلب", key=f"done_ord_{o_id}"
                    ):
                        cursor.execute(
                            "UPDATE orders SET order_status = 'تم التوصيل' WHERE id = ?",
                            (o_id,),
                        )
                        conn.commit()
                        st.success("تم تسليم الطلب وإغلاقه بنجاح!")
                        st.rerun()

                wa_cust_link = f"https://wa.me/{o_cphone}?text=مرحباً، معك كابتن التوصيل من بوابة الكرك بخصوص طلبك رقم #{o_id}، أنا في الطريق إليك."
                st.markdown(
                    f"""
                    <a href="{wa_cust_link}" target="_blank">
                        <button style="background-color: #25D366; color: white; border: none; padding: 10px 15px; border-radius: 8px; font-weight: bold; cursor: pointer; width: 100%; margin-top: 10px;">
                            💬 مراسلة الزبون عبر الواتساب برقم الهاتف
                        </button>
                    </a>
                """,
                    unsafe_allow_html=True,
                )

            st.markdown("---")
    else:
        st.info("لا توجد طلبات توصيل متاحة حالياً.")

    conn.close()
