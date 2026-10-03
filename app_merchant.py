import os
import re
import sqlite3
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="بوابة المتاجر - Karak Gate", page_icon="🔔", layout="wide"
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
    cursor.execute("ALTER TABLE products ADD COLUMN quantity TEXT")
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

st.title("🏬 بوابة المتاجر الشاملة - Karak Gate")

if "merchant_step" not in st.session_state:
  st.session_state.merchant_step = "login_or_register"

if st.session_state.merchant_step == "login_or_register":
  st.subheader("👋 أهلاً بك في بوابة تجار الكرك")
  choice = st.radio(
      "اختر العملية:",
      ["تسجيل دخول متجر مسجل مسبقاً", "تسجيل متجر جديد لأول مرة"],
  )

  if choice == "تسجيل دخول متجر مسجل مسبقاً":
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, category, location, status, phone FROM merchants WHERE status = 'معتمد'")
    all_m = cursor.fetchall()
    conn.close()

    if not all_m:
      st.info(
          "لا توجد أي متاجر معتمدة حالياً. يرجى اختيار 'تسجيل متجر جديد لأول مرة'."
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
                "SELECT id, name, category, location, status, phone FROM merchants WHERE phone = ? AND status = 'معتمد'",
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
                  "⚠️ رقم الهاتف غير معتمد أو غير مسجل بعد لدى الإدارة. يرجى الانتظار حتى يتم اعتماد طلبك."
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
      st.markdown("### 📜 الشروط والأحكام والسياسات الخاصة بـ بوابة الكرك")
      st.markdown(
          """
            1. الالتزام بجودة المنتجات والأسعار المعتمدة.
            2. خصم نسبة 10% كعمولة تشغيلية لبوابة الكرك من إجمالي أصناف المتجر فقط.
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
                (reg_name, reg_cat, reg_phone, full_loc_data, "قيد المراجعة", m_img_path),
            )
            conn.commit()
            conn.close()
            st.success(
                "🎉 تم إرسال طلب انضمام متجرك بنجاح إلى الإدارة! سيتم مراجعته واعتماده قريباً لتتمكن من الدخول."
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
      st.image(m_img_path, width=130)
    else:
      st.write("🏬 **[لا توجد صورة للمتجر]**")
  with col_info:
    st.success(f"✅ لوحة تحكم المتجر: {m_name} | التصنيف: {m_cat}")
    st.info(f"📍 بيانات وموقع المتجر: {m_loc} | 📞 الهاتف: {m_phone}")

  if st.button("⬅️ تسجيل الخروج / تبديل المتجر"):
    if "logged_merchant" in st.session_state:
      del st.session_state.logged_merchant
    if "logged_merchant_id" in st.session_state:
      del st.session_state.logged_merchant_id
    st.session_state.merchant_step = "login_or_register"
    st.rerun()

  conn = get_db()
  cursor = conn.cursor()

  try:
    cursor.execute(
        "SELECT COUNT(*) FROM orders WHERE order_status = 'قيد التجهيز' AND"
        " order_details LIKE ?",
        (f"%{m_name}%",),
    )
    pending_orders_count = cursor.fetchone()[0]
  except:
    pending_orders_count = 0

  if pending_orders_count > 0:
    st.markdown(
        f"""
            <div class="bell-alert">
                🔔 تنبيه هام: يوجد ({pending_orders_count}) طلب جديد موجه إلى متجرك من بوابة الكرك بحاجة لتجهيزه الفوري!
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
            oscillator.frequency.setValueAtTime(880, audioCtx.currentTime);
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

  tab1, tab2, tab3, tab4 = st.tabs([
      "📋 إدارة الأصناف والقوائم",
      "🏷️ العروض والتخفيضات",
      "📦 طلبات المتجر الواردة ومتابعة السائقين",
      "⚙️ تعديل معلومات وصورة المتجر",
  ])

  with tab1:
    st.subheader(f"📋 إضافة الأصناف وقائمة الأطعمة/المنتجات لمتجر: {m_name}")
    with st.form("merchant_add_prod"):
      p_name = st.text_input(
          "اسم الصنف أو الوجبة (مثال: منسف لحم، صحن حمص، ساندويش فلافل)"
      )
      c1, c2 = st.columns(2)
      with c1:
        p_qty = st.text_input("الكمية المتوفرة", value="1")
      with c2:
        p_unit = st.selectbox(
            "الوحدة",
            [
                "وجبة",
                "حبه",
                "عدد",
                "صحن",
                "كيلو",
                "غرام",
                "باكيت",
                "عبوة",
                "لتر",
                "قطعة",
                "دستة",
            ],
        )

      p_price = st.number_input(
          "السعر بالدينار الأردني", min_value=0.1, value=1.0, step=0.25
      )
      p_img = st.file_uploader("صورة الصنف", type=["jpg", "png", "jpeg"])

      submit_p = st.form_submit_button("إضافة الصنف للقائمة")
      if submit_p and p_name:
        img_path = ""
        if p_img is not None:
          img_path = os.path.join(UPLOAD_DIR, p_img.name)
          with open(img_path, "wb") as f:
            f.write(p_img.getbuffer())

        cursor.execute(
            """
                INSERT INTO products (merchant_name, item_name, price, quantity, unit, image_path)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
            (m_name, p_name, p_price, p_qty, p_unit, img_path),
        )
        conn.commit()
        st.success(f"تم إضافة الصنف ({p_name}) بنجاح!")
        st.rerun()

    st.markdown("---")
    st.subheader("📋 قائمة الأصناف الحالية في متجرك (مع الصور والتفاصيل):")

    cursor.execute(
        "SELECT id, item_name, quantity, unit, price, image_path FROM products WHERE"
        " merchant_name = ?",
        (m_name,),
    )
    prods = cursor.fetchall()

    if prods:
      for p in prods:
        p_id, p_name, p_qty, p_unit, p_price, p_img = p

        col_p_img, col_p_info, col_p_del = st.columns([1, 4, 1])
        with col_p_img:
          if p_img and os.path.exists(p_img):
            st.image(p_img, width=80)
          else:
            st.write("📷 [لا توجد صورة]")
        with col_p_info:
          st.markdown(
              f"""
                    <div class="item-card">
                        <p style="margin: 0; font-size: 18px; font-weight: bold; color: #000000;">🍽️ {p_name}</p>
                        <p style="margin: 5px 0 0 0; color: #333333;">الكمية المتوفرة: <b>{p_qty} {p_unit}</b> | السعر: <b>{p_price} دينار أردني</b></p>
                    </div>
                    """,
              unsafe_allow_html=True,
          )
        with col_p_del:
          if st.button("🗑️ حذف", key=f"del_item_{p_id}"):
            cursor.execute("DELETE FROM products WHERE id = ?", (p_id,))
            conn.commit()
            st.success("تم حذف الصنف بنجاح!")
            st.rerun()
        st.markdown("---")
    else:
      st.info("لا توجد أصناف مضافة حالياً في قائمة متجرك.")

  with tab2:
    st.subheader("🏷️ إضافة عروض وخصومات خاصة بمتجرك")
    with st.form("merchant_offer_form"):
      off_title = st.text_input("عنوان العرض")
      off_desc = st.text_area("تفاصيل العرض")
      off_date = st.text_input("ساري لغاية تاريخ", "2026-11-01")

      sub_off = st.form_submit_button("نشر العرض")
      if sub_off and off_title:
        cursor.execute(
            """
                INSERT INTO offers (merchant_name, title, discount_details, valid_until)
                VALUES (?, ?, ?, ?)
            """,
            (m_name, off_title, off_desc, off_date),
        )
        conn.commit()
        st.success("تم نشر العرض بنجاح!")
        st.rerun()

  with tab3:
    st.subheader(
        "📦 الطلبات الواردة إلى متجرك ومتابعة حالة السائقين (مع خصم 10% من منتجات"
        " متجرك)"
    )

    cursor.execute("PRAGMA table_info(orders)")
    ord_cols = [c[1] for c in cursor.fetchall()]
    if "picked_up" not in ord_cols:
      cursor.execute("ALTER TABLE orders ADD COLUMN picked_up INTEGER DEFAULT 0")

    cursor.execute(
        "SELECT id, customer_name, customer_phone, customer_address, order_details,"
        " total_amount, order_status, driver_name, created_at, picked_up FROM"
        " orders WHERE order_details LIKE ? ORDER BY id DESC",
        (f"%{m_name}%",),
    )
    merchant_orders = cursor.fetchall()

    if merchant_orders:
      for ord_item in merchant_orders:
        (
            o_id,
            o_name,
            o_phone,
            o_addr,
            o_odet,
            o_tot,
            o_stat,
            o_dname,
            o_time,
            o_picked,
        ) = ord_item

        merchant_items_total = 0.0
        lines = o_odet.split("\n")
        for line in lines:
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
            driver_status_text = (
                f"✅ استلم الكابتن ({o_dname}) الطلب وتم تسليمه للزبون وإغلاق"
                " الطلب وإبلاغ الإدارة."
            )
          elif o_picked == 1:
            driver_status_text = (
                f"🛵 استلم الكابتن ({o_dname}) الطلب من المتجر وهو في طريقه للزبون"
                " الآن."
            )
          else:
            driver_status_text = (
                f"📍 الكابتن ({o_dname}) في طريقه إلى المتجر لاستلام الطلب."
            )

        st.markdown(
            f"""
                <div class="merchant-card">
                    <h4>🛒 طلب من بوابة الكرك رقم #{o_id}</h4>
                    <p><b>🕒 وقت الطلب:</b> {o_time} | <b>📌 حالة التجهيز العامة:</b> {o_stat}</p>
                    <p><b>🚚 حالة السائق وتتبع الاستلام:</b> <span style="color: #D84315; font-weight: bold;">{driver_status_text}</span></p>
                    <p><b>السائق المسؤول:</b> {o_dname if o_dname else 'لم يُسند بعد'}</p>
                    <p><b>إجمالي أصناف متجرك:</b> {merchant_items_total:.2f} دينار | <span style="color: #C62828;"><b>عمولة بوابة الكرك (10%):</b> {commission_fee:.2f} دينار</span> | <b>صافي مستحقات المتجر:</b> {net_merchant_amount:.2f} دينار</p>
                    <hr style="border: 0.5px solid #ddd;">
                    <pre style="background-color: #F9F9F9; padding: 10px; border-radius: 5px; color: #000000; border: 1px solid #ddd;">{o_odet}</pre>
                </div>
                """,
            unsafe_allow_html=True,
        )

        if o_stat == "قيد التجهيز":
          if st.button(
              f"✨ تأكيد جاهزية الطلب رقم #{o_id} للتحميل",
              key=f"ready_ord_{o_id}",
          ):
            cursor.execute(
                "UPDATE orders SET order_status = 'جاهز للاستلام' WHERE id = ?",
                (o_id,),
            )
            conn.commit()
            st.success(
                "تم تحديث حالة الطلب بأنه جاهز للاستلام وتم إشعار السائق والإدارة!"
            )
            st.rerun()
        st.markdown("---")
    else:
      st.info("لا توجد طلبات واردة لمتجرك حتى الآن.")

  with tab4:
    st.subheader("⚙️ تعديل بيانات ومعلومات وصورة المتجر")

    edit_name = st.text_input("اسم المتجر", value=m_name, key="edit_m_name")
    edit_cat = st.selectbox(
        "التصنيف الرئيسي",
        [
            "مطاعم",
            "حلويات",
            "ماركت",
            "محامص ومكسرات",
            "خضروات وفواكه",
            "لحوم",
            "صيدليات ومستلزمات طبيه",
        ],
        index=(
            [
                "مطاعم",
                "حلويات",
                "ماركت",
                "محامص ومكسرات",
                "خضروات وفواكه",
                "لحوم",
                "صيدليات ومستلزمات طبيه",
            ].index(m_cat)
            if m_cat
            in [
                "مطاعم",
                "حلويات",
                "ماركت",
                "محامص ومكسرات",
                "خضروات وفواكه",
                "لحوم",
                "صيدليات ومستلزمات طبيه",
            ]
            else 0
        ),
        key="edit_m_cat",
    )
    edit_phone = st.text_input("رقم الهاتف", value=m_phone, key="edit_m_phone")
    edit_loc = st.text_input(
        "العنوان ووصف الموقع", value=m_loc, key="edit_m_loc"
    )

    st.markdown("### 📷 رفع أو تحديث صورة المتجر الرئيسية")
    edit_img = st.file_uploader(
        "اختر صورة المتجر (JPG, PNG)", type=["jpg", "png", "jpeg"], key="edit_m_img_upload"
    )

    if st.button("حفظ التعديلات وتحديث المتجر"):
      new_img_path = m_img_path
      if edit_img is not None:
        new_img_path = os.path.join(UPLOAD_DIR, edit_img.name)
        with open(new_img_path, "wb") as f:
          f.write(edit_img.getbuffer())

      cursor.execute(
          """
                UPDATE merchants SET name = ?, category = ?, phone = ?, location = ?, image_path = ? WHERE id = ?
            """,
          (
              edit_name,
              edit_cat,
              edit_phone,
              edit_loc,
              new_img_path,
              st.session_state.logged_merchant_id,
          ),
      )
      conn.commit()
      st.success("تم تحديث بيانات وصورة المتجر بنجاح!")
      st.rerun()

  conn.close()
