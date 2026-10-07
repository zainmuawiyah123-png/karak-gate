"""بوابة السائقين (Streamlit + Supabase) - نسخة محوّلة من تطبيقك الأصلي (SQLite) مع الخريطة والأجرة والإشعارات.
تحتاج في Secrets: SUPABASE_URL, SUPABASE_SERVICE_KEY, VAPID_PRIVATE_KEY, VAPID_EMAIL
"""
import html
import urllib.parse

import streamlit as st

from db import get_sb
from driver_map import render_driver_order, fee_for
from streamlit_integration import capture_subscription

st.set_page_config(page_title="بوابة السائقين - Karak Gate", page_icon="🛵", layout="wide")

st.markdown(
    """
    <style>
    #MainMenu {visibility: hidden;}
    .stDeployButton {display: none;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    .stApp {background-color: #FF5722 !important; color: #000000 !important;}
    h1, h2, h3, h4, h5, h6, p, label, span, div {color: #000000 !important;}
    .stButton>button {border-radius: 8px; font-weight: bold; border: none;
        background-color: #FFFFFF !important; color: #FF5722 !important;}
    .stButton>button:hover {background-color: #FFF3E0 !important; color: #E64A19 !important;}
    .driver-card {background-color: #FFFFFF; padding: 20px; border-radius: 12px; margin-bottom: 15px;
        border: 2px solid #E0E0E0; box-shadow: 0 4px 6px rgba(0,0,0,0.1);}
    .driver-card h4, .driver-card p, .driver-card span {color: #000000 !important;}
    @keyframes pulse {0% {transform: scale(1);} 50% {transform: scale(1.05);} 100% {transform: scale(1);}}
    .bell-alert {background-color: #B71C1C; color: white !important; padding: 15px; border-radius: 10px;
        text-align: center; font-weight: bold; font-size: 20px; animation: pulse 1s infinite;
        margin-bottom: 20px; border: 2px solid yellow;}
    .bell-alert span, .bell-alert div {color: white !important;}
    </style>
    """,
    unsafe_allow_html=True,
)

sb = get_sb()
esc = lambda v: html.escape(str(v if v is not None else ""))


def wa_number(phone):
    """يحوّل 079xxxxxxx إلى 96279xxxxxxx ليعمل رابط واتساب."""
    d = "".join(ch for ch in str(phone or "") if ch.isdigit())
    if d.startswith("00"):
        d = d[2:]
    if d.startswith("0"):
        d = "962" + d[1:]
    return d


def store_name_from(details):
    if "المتجر: " in (details or ""):
        try:
            return details.split("المتجر: ")[1].split("]")[0].split("\n")[0].strip()
        except Exception:
            pass
    return "المتجر المعني"


st.title("🛵 بوابة السائقين ومناديب التوصيل - Karak Gate")

if "driver_step" not in st.session_state:
    st.session_state.driver_step = "login_or_register"

# ---------------------------------------------------------------- دخول / تسجيل
if st.session_state.driver_step == "login_or_register":
    st.subheader("👋 أهلاً بك في بوابة السائقين والكابتن")
    choice = st.radio("اختر العملية:", ["تسجيل دخول سائق مسجل مسبقاً", "تسجيل سائق جديد لأول مرة"])

    if choice == "تسجيل دخول سائق مسجل مسبقاً":
        all_d = sb.table("drivers").select("id,name,vehicle_type,phone").execute().data or []
        if not all_d:
            st.info("لا توجد أي سائقين مسجلين حالياً. يرجى اختيار 'تسجيل سائق جديد لأول مرة'.")
        else:
            d_options = {f"{d['name']} ({d.get('vehicle_type','')} - هاتف: {d['phone']})": d for d in all_d}
            selected_key = st.selectbox("اختر اسمك أو ابحث برقم هاتفك:", list(d_options.keys()))
            quick_phone = st.text_input("أو أدخل رقم هاتفك للتحقق المباشر والدخول:", "")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("دخول لوحة السائق المختارة"):
                    st.session_state.logged_driver_id = d_options[selected_key]["id"]
                    st.session_state.driver_step = "dashboard"
                    st.rerun()
            with c2:
                if st.button("تحقق ودخول برقم الهاتف"):
                    if quick_phone:
                        found = next((d for d in all_d if str(d["phone"]) == quick_phone.strip()), None)
                        if found:
                            st.session_state.logged_driver_id = found["id"]
                            st.session_state.driver_step = "dashboard"
                            st.rerun()
                        else:
                            st.warning("⚠️ رقم الهاتف غير مسجل مسبقاً. يرجى التسجيل كسايق جديد.")
                    else:
                        st.error("الرجاء إدخال رقم الهاتف أولاً.")
    else:
        with st.form("new_driver_reg"):
            st.subheader("📝 نموذج انضمام سائق جديد للإدارة")
            d_name = st.text_input("الاسم الكامل للسائق")
            d_phone = st.text_input("رقم الهاتف المحمول (للتواصل ودخول البوابة)")
            d_vehicle = st.selectbox("نوع وسيلة النقل",
                                     ["دراجة نارية (موتوسيكل)", "سيارة خاصة", "سكوتر", "سرفيس/بايك"])
            if st.form_submit_button("إرسال طلب الانضمام كسايق"):
                if not d_name or not d_phone:
                    st.error("الرجاء إدخال الاسم ورقم الهاتف.")
                else:
                    try:
                        sb.table("drivers").insert({"name": d_name, "phone": d_phone.strip(),
                                                    "vehicle_type": d_vehicle, "status": "متاح"}).execute()
                        st.success("🎉 تم تسجيلك بنجاح! يمكنك الآن تسجيل الدخول برقم هاتفك.")
                    except Exception as e:
                        st.error(f"عطل أو رقم الهاتف مستخدم مسبقاً: {e}")

# ---------------------------------------------------------------- لوحة السائق
elif st.session_state.driver_step == "dashboard":
    rows = sb.table("drivers").select("*").eq("id", st.session_state.logged_driver_id).execute().data or []
    if not rows:
        st.session_state.driver_step = "login_or_register"
        st.rerun()
    drv = rows[0]
    d_id, d_name = drv["id"], drv["name"]

    capture_subscription("driver", d_id)   # يحفظ جهاز السائق لاستلام الإشعارات

    st.success(f"✅ لوحة تحكم السائق: الكابتن {d_name} | الوسيلة: {drv.get('vehicle_type','')} | الهاتف: {drv.get('phone','')}")
    b1, b2 = st.columns(2)
    if b1.button("⬅ تسجيل الخروج / تبديل الحساب"):
        for k in ("logged_driver_id",):
            st.session_state.pop(k, None)
        st.session_state.driver_step = "login_or_register"
        st.rerun()
    if b2.button("🔄 تحديث الطلبات"):
        st.rerun()

    all_orders = (sb.table("orders").select("*").neq("order_status", "تم التوصيل")
                  .order("id", desc=True).limit(200).execute().data or [])
    my_orders = [o for o in all_orders if o.get("driver_name") == d_name]
    open_orders = [o for o in all_orders if not o.get("driver_name")]
    shown = my_orders + open_orders

    if my_orders:
        st.markdown(f"""<div class="bell-alert">🔔 تنبيه هام: يوجد لديك ({len(my_orders)}) طلب مسند من الإدارة بحاجة للتوصيل الفوري!</div>""",
                    unsafe_allow_html=True)
        st.components.v1.html("""<script>
        try{const a=new (window.AudioContext||window.webkitAudioContext)();const o=a.createOscillator();
        const g=a.createGain();o.type='sine';o.frequency.setValueAtTime(660,a.currentTime);
        g.gain.setValueAtTime(0.3,a.currentTime);o.connect(g);g.connect(a.destination);o.start();
        o.stop(a.currentTime+0.4);}catch(e){}</script>""", height=0)

    st.markdown("---")
    st.subheader("📦 الطلبات المتاحة والمسندة إليك:")

    merchants_cache = {}
    if not shown:
        st.info("لا توجد طلبات توصيل متاحة حالياً.")

    for o in shown:
        o_id = o["id"]
        is_mine = o.get("driver_name") == d_name
        o_det = o.get("order_details") or ""
        o_pay = o.get("payment_method") or ""
        store = store_name_from(o_det)
        if store not in merchants_cache:
            mr = sb.table("merchants").select("*").eq("name", store).execute().data or []
            merchants_cache[store] = mr[0] if mr else None
        merchant = merchants_cache[store]
        picked = bool(o.get("picked_up"))
        cash_done = bool(o.get("cash_collected"))

        st.markdown(f"""
        <div class="driver-card">
            <h4>🛒 طلب رقم #{o_id} {'(مسند إليك)' if is_mine else '(متاح للاستلام)'}</h4>
            <p><b>🕒 وقت الطلب:</b> {esc(o.get('created_at'))} | <b>📌 حالة الطلب:</b> {esc(o.get('order_status'))} | <b>💳 طريقة الدفع:</b> {esc(o_pay)}</p>
            <p><b>المتجر المطلوب منه:</b> {esc(store)}</p>
            <hr style="border: 0.5px solid #ccc;">
            <pre style="background-color:#F9F9F9;padding:10px;border-radius:5px;color:#000;border:1px solid #ddd;white-space:pre-wrap;">{esc(o_det)}</pre>
            <p><b>المبلغ الإجمالي المطلوب تحصيله:</b> {esc(o.get('total_amount'))} دينار</p>
        </div>""", unsafe_allow_html=True)

        # ----- المسافة والأجرة والخريطة بين المتجر والزبون (تظهر من لحظة وصول الطلب)
        if merchant:
            render_driver_order(o, merchant, nav="customer" if (is_mine and picked) else "store")
        else:
            st.warning("تعذّر تحديد المتجر من تفاصيل الطلب، تواصل مع الإدارة.")

        # ----- طلب غير مسند: استلام المهمة
        if not is_mine:
            if st.button("🙋‍♂️ استلام مهمة التوصيل", key=f"take_{o_id}", use_container_width=True):
                fresh = sb.table("orders").select("driver_name").eq("id", o_id).execute().data or [{}]
                if fresh[0].get("driver_name"):
                    st.error("سبقك سائق آخر على هذا الطلب.")
                else:
                    upd = {"driver_name": d_name, "order_status": "جاري التوصيل"}
                    fee, _ = fee_for(o, merchant)
                    if fee is not None:
                        upd["driver_fee"] = fee
                    sb.table("orders").update(upd).eq("id", o_id).execute()
                    st.success("تم استلام المهمة بنجاح!")
                    st.rerun()
            st.markdown("---")
            continue

        # ----- المرحلة الأولى: التوجه للمتجر
        if not picked:
            st.markdown("### 🗺️ المرحلة الأولى: التوجه إلى المتجر لاستلام الطلب")
            if merchant:
                st.info(f"عنوان وموقع المتجر: {merchant.get('location','')}")
            if st.button("✅ تم استلام الطلب من المتجر (الانتقال للمرحلة الثانية)", key=f"pickup_{o_id}",
                         use_container_width=True):
                sb.table("orders").update({"picked_up": 1, "order_status": "جاري التوصيل"}).eq("id", o_id).execute()
                st.success("تم تأكيد الاستلام من المتجر وانتقلت للمرحلة الثانية!")
                st.rerun()

        # ----- المرحلة الثانية: التوصيل للزبون
        else:
            st.markdown("### 📍 المرحلة الثانية: التوصيل إلى الزبون (الخصوصية والاتصال والموقع)")
            st.markdown(f"""
            <div style="background-color:#FFF3E0;padding:15px;border-radius:10px;margin-bottom:15px;border:1px solid #FF5722;">
                <p style="font-size:18px;color:#D84315;margin-bottom:5px;"><b>📞 رقم هاتف الزبون:</b> {esc(o.get('customer_phone'))} <span style="font-size:14px;color:#333;">(بدون اسم لحفظ الخصوصية)</span></p>
                <p style="font-size:16px;margin-bottom:0;color:#000;"><b>📍 العنوان العادي المسجل:</b> {esc(o.get('customer_address'))}</p>
            </div>""", unsafe_allow_html=True)

            s1, s2 = st.columns(2)
            if "نقداً" in o_pay:
                with s1:
                    if not cash_done:
                        if st.button("💵 تأكيد استلام المبلغ نقداً وتسليمه للإدارة", key=f"cash_{o_id}"):
                            sb.table("orders").update({"cash_collected": 1}).eq("id", o_id).execute()
                            st.success("تم تسجيل استلام المبلغ نقداً وإبلاغ الإدارة بنجاح!")
                            st.rerun()
                    else:
                        st.success("✅ تم تأكيد استلام المبلغ نقداً مسبقاً.")
            with s2:
                if st.button("🏁 تأكيد تسليم الطلب للزبون وإغلاق الطلب", key=f"done_{o_id}"):
                    sb.table("orders").update({"order_status": "تم التوصيل"}).eq("id", o_id).execute()
                    st.success("تم تسليم الطلب وإغلاقه بنجاح!")
                    st.rerun()

            wa_msg = urllib.parse.quote(f"مرحباً، معك كابتن التوصيل من Halago بخصوص طلبك رقم #{o_id}، أنا في الطريق إليك.")
            st.link_button("💬 مراسلة الزبون عبر الواتساب", f"https://wa.me/{wa_number(o.get('customer_phone'))}?text={wa_msg}",
                           use_container_width=True)
        st.markdown("---")
