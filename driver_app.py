"""بوابة السائقين (Streamlit + Supabase): دخول بـ PIN، طلباتي، خريطة ومسافة وأجرة، جرس تنبيه، وإشعار الإدارة عند التسليم/استلام النقد."""
import html
import urllib.parse

import streamlit as st

from db import get_sb
from driver_map import render_driver_order, fee_for
from streamlit_integration import capture_subscription
from auth_pin import (valid_pin, valid_phone, norm_phone, set_pin, find_by_phone, check_pin, NO_PIN)

try:
    from push_service import send_push
    PUSH_IMPORT_OK = True
except Exception:
    PUSH_IMPORT_OK = False

st.set_page_config(page_title="بوابة السائقين - Halago", page_icon="🛵", layout="wide")

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
PUSH_ON = PUSH_IMPORT_OK
esc = lambda v: html.escape(str(v if v is not None else ""))


def wa_number(phone):
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


def notify_admin(text):
    if PUSH_ON:
        try:
            send_push("admin", 0, "Halago - السائق", text)
        except Exception:
            pass



def run_script_html(code):
    """يشغّل سكربت JS صغيرًا (للجرس) بدون استخدام الواجهة القديمة المُهمَلة."""
    if hasattr(st, "iframe"):
        try:
            st.iframe(code, height=1)
            return
        except Exception:
            pass
    st.components.v1.html(code, height=0)


def autorefresh(seconds=12):
    try:
        from streamlit_autorefresh import st_autorefresh
        st_autorefresh(interval=seconds * 1000, key="driver_auto_refresh")
    except Exception:
        pass


BELL_JS = """<script>
try{const a=new (window.AudioContext||window.webkitAudioContext)();
[0,0.35,0.7].forEach(function(t){const o=a.createOscillator();const g=a.createGain();
o.type='sine';o.frequency.setValueAtTime(880,a.currentTime+t);g.gain.setValueAtTime(0.35,a.currentTime+t);
o.connect(g);g.connect(a.destination);o.start(a.currentTime+t);o.stop(a.currentTime+t+0.25);});}catch(e){}
</script>"""

st.title("🛵 بوابة السائقين ومناديب التوصيل - Halago")

if "driver_step" not in st.session_state:
    st.session_state.driver_step = "login_or_register"

# ---------------------------------------------------------------- دخول / تسجيل
if st.session_state.driver_step == "login_or_register":
    st.subheader("👋 أهلاً بك في بوابة السائقين والكابتن")
    choice = st.radio("اختر العملية:", ["تسجيل دخول سائق مسجل مسبقاً", "تسجيل سائق جديد لأول مرة"], horizontal=True)

    if choice == "تسجيل دخول سائق مسجل مسبقاً":
        with st.form("driver_login"):
            phone = st.text_input("رقم هاتفك")
            pin = st.text_input("رمز PIN (4 أرقام)", type="password", max_chars=4)
            go = st.form_submit_button("دخول")
        if go:
            if not valid_phone(phone) or not valid_pin(pin):
                st.error("أدخل رقم هاتف صحيح ورمز PIN من 4 أرقام.")
            else:
                row = find_by_phone(sb, "drivers", phone)
                if not row:
                    st.error("الرقم غير مسجل. سجّل كسائق جديد أو تواصل مع الإدارة.")
                else:
                    ok, msg = check_pin(sb, "drivers", row, pin)
                    if msg == NO_PIN:
                        st.warning("حسابك مسجّل قبل تفعيل رمز PIN. تواصل مع الإدارة لتعيين رمز PIN لك.")
                    elif not ok:
                        st.error(msg)
                    elif row.get("status") == "قيد المراجعة":
                        st.warning("⏳ طلب انضمامك قيد المراجعة من الإدارة. سيتم تفعيل حسابك قريبًا.")
                    else:
                        st.session_state.logged_driver_id = row["id"]
                        st.session_state.driver_step = "dashboard"
                        st.rerun()
    else:
        with st.form("new_driver_reg"):
            st.subheader("📝 نموذج انضمام سائق جديد للإدارة")
            d_name = st.text_input("الاسم الكامل للسائق")
            d_phone = st.text_input("رقم الهاتف المحمول (للتواصل ودخول البوابة)")
            c1, c2 = st.columns(2)
            with c1:
                d_pin = st.text_input("اختر رمز PIN (4 أرقام)", type="password", max_chars=4)
            with c2:
                d_pin2 = st.text_input("أعد كتابة PIN", type="password", max_chars=4)
            d_vehicle = st.selectbox("نوع وسيلة النقل", ["دراجة نارية (موتوسيكل)", "سيارة خاصة", "سكوتر", "سرفيس/بايك"])
            go = st.form_submit_button("إرسال طلب الانضمام كسائق")
        if go:
            if not d_name.strip() or not valid_phone(d_phone):
                st.error("الرجاء إدخال الاسم ورقم هاتف صحيح.")
            elif not valid_pin(d_pin) or d_pin != d_pin2:
                st.error("رمز PIN يجب أن يكون 4 أرقام ومتطابقًا في الخانتين.")
            elif find_by_phone(sb, "drivers", d_phone):
                st.error("هذا الرقم مسجّل مسبقًا.")
            else:
                try:
                    np_ = norm_phone(d_phone)
                    res = sb.table("drivers").insert({"name": d_name.strip(), "phone": np_,
                                                      "vehicle_type": d_vehicle, "status": "قيد المراجعة"}).execute()
                    set_pin(sb, "drivers", res.data[0]["id"], np_, d_pin)
                    st.success("🎉 تم إرسال طلبك للإدارة. ستتمكن من الدخول بعد تفعيل حسابك.")
                    notify_admin(f"طلب انضمام سائق جديد: {d_name.strip()}")
                except Exception as e:
                    st.error(f"تعذر التسجيل: {e}")

# ---------------------------------------------------------------- لوحة السائق
elif st.session_state.driver_step == "dashboard":
    rows = sb.table("drivers").select("*").eq("id", st.session_state.logged_driver_id).execute().data or []
    if not rows or rows[0].get("status") == "قيد المراجعة":
        st.session_state.driver_step = "login_or_register"
        st.rerun()
    drv = rows[0]
    d_id, d_name = drv["id"], drv["name"]

    capture_subscription("driver", d_id)
    autorefresh(12)

    st.success(f"✅ لوحة تحكم السائق: الكابتن {d_name} | الوسيلة: {drv.get('vehicle_type','')} | الهاتف: {drv.get('phone','')}")
    st.caption("🔔 لتصلك إشعارات الطلبات حتى والتطبيق مغلق: افتح البوابة من أيقونتها على الشاشة الرئيسية ووافق على الإشعارات.")
    b1, b2 = st.columns(2)
    if b1.button("⬅ تسجيل الخروج / تبديل الحساب"):
        st.session_state.pop("logged_driver_id", None)
        st.session_state.driver_step = "login_or_register"
        st.rerun()
    if b2.button("🔄 تحديث الطلبات"):
        st.rerun()

    all_orders = (sb.table("orders").select("*").neq("order_status", "تم التوصيل")
                  .order("id", desc=True).limit(200).execute().data or [])
    my_orders = [o for o in all_orders if o.get("driver_name") == d_name]
    open_orders = [o for o in all_orders if not o.get("driver_name") and o.get("order_status") != "ملغي"]
    shown = my_orders + open_orders

    # الجرس: يرنّ فقط عند ظهور طلب جديد مسند إليه (وليس مع كل تحديث)
    my_ids = {o["id"] for o in my_orders}
    known = st.session_state.get("driver_known_ids")
    if my_orders:
        st.markdown(f"""<div class="bell-alert">🔔 تنبيه هام: يوجد لديك ({len(my_orders)}) طلب مسند من الإدارة بحاجة للتوصيل الفوري!</div>""",
                    unsafe_allow_html=True)
    if known is None or (my_ids - known):
        if my_ids:
            run_script_html(BELL_JS)
    st.session_state.driver_known_ids = my_ids

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

        # المسافة والأجرة للجميع؛ الخريطة (موقع الزبون) فقط لصاحب الطلب المسند
        if merchant:
            render_driver_order(o, merchant, nav="customer" if (is_mine and picked) else "store", show_map=is_mine)
        else:
            st.warning("تعذّر تحديد المتجر من تفاصيل الطلب، تواصل مع الإدارة.")

        if not is_mine:
            if st.button("🙋‍♂️ استلام مهمة التوصيل", key=f"take_{o_id}", use_container_width=True):
                fresh = sb.table("orders").select("driver_name").eq("id", o_id).execute().data or [{}]
                if fresh[0].get("driver_name"):
                    st.error("سبقك سائق آخر على هذا الطلب.")
                else:
                    upd = {"driver_name": d_name, "order_status": "جاري التوصيل"}
                    fee, _ = fee_for(o, merchant) if merchant else (None, None)
                    if fee is not None:
                        upd["driver_fee"] = fee
                    sb.table("orders").update(upd).eq("id", o_id).execute()
                    notify_admin(f"الكابتن {d_name} استلم مهمة توصيل الطلب #{o_id}")
                    st.success("تم استلام المهمة بنجاح!")
                    st.rerun()
            st.markdown("---")
            continue

        if not picked:
            st.markdown("### 🗺️ المرحلة الأولى: التوجه إلى المتجر لاستلام الطلب")
            if merchant:
                st.info(f"عنوان وموقع المتجر: {merchant.get('location','')}")
            if st.button("✅ تم استلام الطلب من المتجر (الانتقال للمرحلة الثانية)", key=f"pickup_{o_id}",
                         use_container_width=True):
                sb.table("orders").update({"picked_up": 1, "order_status": "جاري التوصيل"}).eq("id", o_id).execute()
                notify_admin(f"الكابتن {d_name} استلم الطلب #{o_id} من {store} وهو في الطريق للزبون")
                st.success("تم تأكيد الاستلام من المتجر وانتقلت للمرحلة الثانية!")
                st.rerun()
        else:
            st.markdown("### 📍 المرحلة الثانية: التوصيل إلى الزبون (الخصوصية والاتصال والموقع)")
            st.markdown(f"""
            <div style="background-color:#FFF3E0;padding:15px;border-radius:10px;margin-bottom:15px;border:1px solid #FF5722;">
                <p style="font-size:18px;color:#D84315;margin-bottom:5px;"><b>📞 رقم هاتف الزبون:</b> {esc(o.get('customer_phone'))} <span style="font-size:14px;color:#333;">(بدون اسم لحفظ الخصوصية)</span></p>
                <p style="font-size:16px;margin-bottom:0;color:#000;"><b>📍 العنوان العادي المسجل:</b> {esc(o.get('customer_address'))}</p>
            </div>""", unsafe_allow_html=True)

            is_cash = "نقد" in o_pay
            s1, s2 = st.columns(2)
            if is_cash:
                with s1:
                    if not cash_done:
                        if st.button("💵 تأكيد استلام المبلغ نقداً وتسليمه للإدارة", key=f"cash_{o_id}"):
                            sb.table("orders").update({"cash_collected": 1}).eq("id", o_id).execute()
                            notify_admin(f"الكابتن {d_name} استلم {o.get('total_amount')} د.أ نقدًا للطلب #{o_id}")
                            st.success("تم تسجيل استلام المبلغ نقداً وإبلاغ الإدارة بنجاح!")
                            st.rerun()
                    else:
                        st.success("✅ تم تأكيد استلام المبلغ نقداً مسبقاً.")
            with s2:
                blocked = is_cash and not cash_done
                if st.button("🏁 تأكيد تسليم الطلب للزبون وإغلاق الطلب", key=f"done_{o_id}", disabled=blocked):
                    sb.table("orders").update({"order_status": "تم التوصيل"}).eq("id", o_id).execute()
                    notify_admin(f"تم توصيل الطلب #{o_id} بواسطة الكابتن {d_name}"
                                 + (f" واستلام {o.get('total_amount')} د.أ نقدًا" if is_cash else ""))
                    st.success("تم تسليم الطلب وإغلاقه بنجاح!")
                    st.rerun()
            if is_cash and not cash_done:
                st.caption("لإغلاق الطلب أكّد أولًا استلام المبلغ نقدًا.")

            wa_msg = urllib.parse.quote(f"مرحباً، معك كابتن التوصيل من Halago بخصوص طلبك رقم #{o_id}، أنا في الطريق إليك.")
            st.link_button("💬 مراسلة الزبون عبر الواتساب", f"https://wa.me/{wa_number(o.get('customer_phone'))}?text={wa_msg}",
                           use_container_width=True)
        st.markdown("---")
