import re
import base64  # noqa: F401  (يُستخدم عند عرض الصور القديمة المخزنة كنص)

import streamlit as st
from supabase import create_client

from auth_pin import (valid_pin, valid_phone, norm_phone, set_pin, find_by_phone, check_pin, NO_PIN)

# ---- أدوات الحزمة (اختيارية: إن لم تُرفع الملفات يعمل التطبيق بدونها) ----
try:
    from catalog_tools import render_bulk_import, save_uploaded_image
    CATALOG_OK = True
except Exception:
    CATALOG_OK = False

try:
    from streamlit_integration import capture_subscription
except Exception:
    def capture_subscription(role, owner_key):
        return None

try:
    from driver_map import coords_from_map_link
except Exception:
    coords_from_map_link = None

try:
    from push_service import send_push
    PUSH_IMPORT_OK = True
except Exception:
    PUSH_IMPORT_OK = False


def push_ready():
    try:
        return bool(st.secrets.get("SUPABASE_SERVICE_KEY")) and bool(st.secrets.get("VAPID_PRIVATE_KEY"))
    except Exception:
        return False


PUSH_ON = PUSH_IMPORT_OK and push_ready()
COMMISSION = 0.10
PAGE = 15
CATEGORIES = ["مطاعم", "حلويات", "ماركت", "محامص ومكسرات", "خضروات وفواكه", "لحوم", "صيدليات ومستلزمات طبيه"]

st.set_page_config(page_title="بوابة المتاجر - Halago", page_icon="🔔", layout="wide")

st.markdown(
    """
    <style>
    #MainMenu {visibility: hidden;}
    .stDeployButton {display: none;}
    header {visibility: hidden;}
    footer {visibility: hidden;}

    .stApp { background-color: #FF5722 !important; color: #000000 !important; }
    h1, h2, h3, h4, h5, h6, p, label, span { color: #000000 !important; }
    .stButton>button {
        border-radius: 8px; font-weight: bold; border: none;
        background-color: #FFFFFF !important; color: #FF5722 !important;
    }
    .stButton>button:hover { background-color: #FFF3E0 !important; color: #E64A19 !important; }
    .merchant-card {
        background-color: #FFFFFF; padding: 20px; border-radius: 12px; margin-bottom: 15px;
        border: 2px solid #E0E0E0; box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .merchant-card h4, .merchant-card p, .merchant-card span { color: #000000 !important; }
    .item-card { background-color: #FFF3E0; padding: 15px; border-radius: 10px; margin-bottom: 10px; border: 1px solid #FFCC80; }
    .item-card p { color: #000000 !important; }
    @keyframes pulse { 0% { transform: scale(1); } 50% { transform: scale(1.05); } 100% { transform: scale(1); } }
    .bell-alert {
        background-color: #B71C1C; color: white !important; padding: 15px; border-radius: 10px;
        text-align: center; font-weight: bold; font-size: 20px; animation: pulse 1s infinite;
        margin-bottom: 20px; border: 2px solid yellow;
    }
    .bell-alert span, .bell-alert div { color: white !important; }
    </style>
""",
    unsafe_allow_html=True,
)

# إعداد Supabase
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


def storage_client():
    """عميل بمفتاح service لرفع الصور إلى Storage (يتوفر فقط إن أُضيف السر)."""
    try:
        if st.secrets.get("SUPABASE_SERVICE_KEY"):
            from db import get_sb
            return get_sb()
    except Exception:
        pass
    return None


STORAGE = storage_client()


def image_from_upload(uploaded, merchant, key):
    if uploaded is None:
        return ""
    if CATALOG_OK:
        return save_uploaded_image(uploaded, STORAGE, merchant, key)
    # بدون catalog_tools: نخزّنها كما هي (قد تكون ثقيلة)
    raw = uploaded.getvalue()
    return "data:image/jpeg;base64," + base64.b64encode(raw).decode("utf-8") if len(raw) < 300_000 else ""


def show_image(value, width=80, fallback="📷"):
    if value and str(value).startswith(("http", "data:image")):
        try:
            st.image(str(value), width=width)
            return
        except Exception:
            pass
    st.markdown(f"<span style='font-size:30px;'>{fallback}</span>", unsafe_allow_html=True)



def run_script_html(code):
    """يشغّل سكربت JS صغيرًا (للجرس) بدون استخدام الواجهة القديمة المُهمَلة."""
    if hasattr(st, "iframe"):
        try:
            st.iframe(code, height=1)
            return
        except Exception:
            pass
    st.components.v1.html(code, height=0)


def autorefresh(seconds=15):
    try:
        from streamlit_autorefresh import st_autorefresh
        st_autorefresh(interval=seconds * 1000, key="merchant_auto_refresh")
    except Exception:
        pass


st.title("🏬 بوابة المتاجر الشاملة - Halago")

if "merchant_step" not in st.session_state:
    st.session_state.merchant_step = "login_or_register"

# ============================================================
# الدخول / التسجيل (هاتف + PIN)
# ============================================================
if st.session_state.merchant_step == "login_or_register":
    st.subheader("👋 أهلاً بك في تجار Halago")
    choice = st.radio("اختر العملية:", ["تسجيل دخول المتجر", "تسجيل متجر جديد لأول مرة"], horizontal=True)

    if choice == "تسجيل دخول المتجر":
        with st.form("merchant_login"):
            phone = st.text_input("رقم هاتف المتجر")
            pin = st.text_input("رمز PIN (4 أرقام)", type="password", max_chars=4)
            go = st.form_submit_button("دخول لوحة التحكم")
        if go:
            if not valid_phone(phone) or not valid_pin(pin):
                st.error("أدخل رقم الهاتف ورمز PIN من 4 أرقام.")
            else:
                row = find_by_phone(sb, "merchants", phone)
                if not row:
                    st.error("لا يوجد متجر بهذا الرقم. سجّل متجرك الجديد أولًا.")
                elif row.get("status") == "موقف":
                    st.error("هذا المتجر موقوف مؤقتًا. تواصل مع الإدارة.")
                else:
                    ok, msg = check_pin(sb, "merchants", row, pin)
                    if ok:
                        st.session_state.logged_merchant_id = row["id"]
                        st.session_state.merchant_step = "dashboard"
                        st.rerun()
                    elif msg == NO_PIN:
                        st.warning("متجرك مسجّل قبل تفعيل رمز PIN. تواصل مع الإدارة لتعيين رمز PIN لك.")
                    else:
                        st.error(msg)
    else:
        with st.form("new_merchant_reg"):
            st.subheader("📝 انضمام متجر جديد")
            reg_name = st.text_input("اسم المتجر الكامل")
            reg_cat = st.selectbox("القسم الرئيسي", CATEGORIES)
            reg_phone = st.text_input("رقم هاتف المتجر (للدخول)")
            c1, c2 = st.columns(2)
            with c1:
                reg_pin = st.text_input("اختر رمز PIN (4 أرقام)", type="password", max_chars=4)
            with c2:
                reg_pin2 = st.text_input("أعد كتابة PIN", type="password", max_chars=4)
            reg_address = st.text_input("العنوان التفصيلي (المدينة، الحي، الشارع)", "الكرك - المرج")
            reg_geo_link = st.text_input("رابط موقع المتجر على خرائط جوجل (Google Maps URL)")
            reg_m_img = st.file_uploader("صورة المتجر الرئيسية (شعار أو واجهة)", type=["jpg", "png", "jpeg"])
            accept_terms = st.checkbox("أوافق على الشروط والأحكام وعمولة التشغيل (10%)")
            submit_reg = st.form_submit_button("تسجيل المتجر والبدء برفع الأصناف")

        if submit_reg:
            if not reg_name.strip() or not valid_phone(reg_phone):
                st.error("أدخل اسم المتجر ورقم هاتف صحيح (07XXXXXXXX).")
            elif not valid_pin(reg_pin) or reg_pin != reg_pin2:
                st.error("رمز PIN يجب أن يكون 4 أرقام ومتطابقًا في الخانتين.")
            elif not accept_terms:
                st.error("يجب الموافقة على الشروط والأحكام للمتابعة.")
            elif find_by_phone(sb, "merchants", reg_phone):
                st.error("هذا الرقم مسجّل لمتجر آخر.")
            else:
                try:
                    np_ = norm_phone(reg_phone)
                    payload = {
                        "name": reg_name.strip(), "category": reg_cat, "phone": np_,
                        "location": reg_address.strip(), "map_link": reg_geo_link.strip(),
                        "status": "قيد المراجعة",
                        "image_data": image_from_upload(reg_m_img, reg_name.strip(), "logo"),
                    }
                    xy = coords_from_map_link(reg_geo_link.strip()) if (coords_from_map_link and reg_geo_link.strip()) else None
                    if xy:
                        payload["lat"], payload["lng"] = xy
                    try:
                        res = sb.table("merchants").insert(payload).execute()
                    except Exception:
                        payload.pop("lat", None)
                        payload.pop("lng", None)
                        res = sb.table("merchants").insert(payload).execute()
                    new_row = (res.data or [{}])[0]
                    set_pin(sb, "merchants", new_row["id"], np_, reg_pin)
                    st.session_state.logged_merchant_id = new_row["id"]
                    st.session_state.merchant_step = "dashboard"
                    st.session_state.just_registered = True
                    st.rerun()
                except Exception as e:
                    st.error(f"تعذر التسجيل: {e}")

# ============================================================
# لوحة التحكم
# ============================================================
elif st.session_state.merchant_step == "dashboard":
    m_id = st.session_state.get("logged_merchant_id")
    try:
        rows = sb.table("merchants").select("*").eq("id", m_id).execute().data or []
    except Exception:
        rows = []
    if not rows:
        st.session_state.merchant_step = "login_or_register"
        st.rerun()
    m_data = rows[0]
    m_name = m_data.get("name", "متجر")
    m_status = m_data.get("status", "")

    capture_subscription("merchant", m_id)   # حفظ جهاز التاجر لاستلام الإشعارات المجانية
    autorefresh(15)

    col_logo, col_info = st.columns([1, 3])
    with col_logo:
        show_image(m_data.get("image_data"), width=120, fallback="🏬")
    with col_info:
        st.success(f"✅ لوحة تحكم المتجر: {m_name} | التصنيف: {m_data.get('category','')}")
        st.info(f"📍 الموقع: {m_data.get('location','')} | 📞 الهاتف: {m_data.get('phone','')}")

    if st.session_state.pop("just_registered", False):
        st.balloons()
    if m_status == "قيد المراجعة":
        st.warning("⏳ متجرك قيد المراجعة. ارفع أصنافك الآن؛ لن يراها الزبائن إلا بعد اعتماد الإدارة للمتجر.")

    st.caption("🔔 لتصلك إشعارات الطلبات حتى والتطبيق مغلق: افتح البوابة من أيقونتها على الشاشة الرئيسية ووافق على الإشعارات.")

    if st.button("⬅️ تسجيل الخروج / تبديل المتجر"):
        st.session_state.pop("logged_merchant_id", None)
        st.session_state.merchant_step = "login_or_register"
        st.rerun()

    tag = f"[المتجر: {m_name}]"
    try:
        recent = (sb.table("orders").select("*").ilike("order_details", f"%{tag}%")
                  .order("id", desc=True).limit(100).execute().data or [])
        merchant_orders = [o for o in recent if tag in str(o.get("order_details", ""))]
    except Exception:
        merchant_orders = []
    pending_orders_count = sum(1 for o in merchant_orders if o.get("order_status") == "قيد التجهيز")

    if pending_orders_count > 0:
        st.markdown(f"""<div class="bell-alert">🔔 تنبيه هام: يوجد ({pending_orders_count}) طلب جديد موجه إلى متجرك بحاجة لتجهيزه الفوري!</div>""",
                    unsafe_allow_html=True)
        seen = st.session_state.get("merchant_seen_pending", 0)
        if pending_orders_count > seen:
            run_script_html("""<script>
            try{const a=new (window.AudioContext||window.webkitAudioContext)();const o=a.createOscillator();
            const g=a.createGain();o.type='sine';o.frequency.setValueAtTime(660,a.currentTime);
            g.gain.setValueAtTime(0.3,a.currentTime);o.connect(g);g.connect(a.destination);o.start();
            o.stop(a.currentTime+0.5);}catch(e){}</script>""")
        st.session_state.merchant_seen_pending = pending_orders_count
    else:
        st.session_state.merchant_seen_pending = 0

    st.markdown("---")
    tab1, tab2, tab3, tab4 = st.tabs([
        "📋 إدارة الأصناف والقوائم",
        "🏷️ العروض والتخفيضات",
        "📦 طلبات المتجر الواردة",
        "⚙️ تعديل معلومات وصورة المتجر",
    ])

    # ---------------- الأصناف ----------------
    with tab1:
        st.subheader(f"📋 أصناف متجر: {m_name}")
        with st.form("merchant_add_prod", clear_on_submit=True):
            p_name = st.text_input("اسم الصنف (مثال: منسف لحم، صحن حمص، ساندويش)")
            c1, c2, c3 = st.columns(3)
            with c1:
                p_qty = st.text_input("الكمية", value="1")
            with c2:
                p_unit = st.selectbox("الوحدة", ["وجبة", "حبة", "عدد", "صحن", "كيلو", "غرام", "باكيت", "عبوة", "لتر", "قطعة", "دستة"])
            with c3:
                p_price = st.number_input("السعر (دينار أردني)", min_value=0.1, value=1.0, step=0.25)
            p_barcode = st.text_input("الباركود (اختياري)")
            p_img_file = st.file_uploader("صورة الصنف", type=["jpg", "png", "jpeg"])
            submit_p = st.form_submit_button("إضافة الصنف للقائمة")
        if submit_p:
            if not p_name.strip():
                st.error("أدخل اسم الصنف.")
            else:
                try:
                    row = {"merchant_name": m_name, "item_name": p_name.strip(), "price": p_price,
                           "quantity": p_qty, "unit": p_unit,
                           "image_path": image_from_upload(p_img_file, m_name, p_name.strip())}
                    if p_barcode.strip():
                        row["barcode"] = p_barcode.strip()
                    sb.table("products").insert(row).execute()
                    st.success(f"تم إضافة الصنف ({p_name}) بنجاح!")
                except Exception as e:
                    st.error(f"خطأ أثناء إضافة الصنف: {e}")

        if CATALOG_OK:
            with st.expander("📥 استيراد أصنافي دفعة واحدة من ملف Excel / CSV (للمتاجر الكبيرة)"):
                render_bulk_import(sb, [m_name], STORAGE, fixed_merchant=m_name)

        st.markdown("---")
        st.subheader("📋 قائمة الأصناف الحالية")
        sq = st.text_input("🔎 ابحث في أصنافك", key="m_prod_q").strip()
        page = st.session_state.get("m_prod_page", 0)
        if st.session_state.get("m_prod_q_prev") != sq:
            page = 0
            st.session_state.m_prod_q_prev = sq
        try:
            qr = sb.table("products").select("id,item_name,price,quantity,unit,image_path", count="exact").eq("merchant_name", m_name)
            if sq:
                qr = qr.ilike("item_name", f"%{sq}%")
            res = qr.order("id", desc=True).range(page * PAGE, page * PAGE + PAGE - 1).execute()
            prods, total = res.data or [], (res.count if res.count is not None else len(res.data or []))
        except Exception:
            prods, total = [], 0
        pages = max(1, -(-total // PAGE))
        st.caption(f"إجمالي الأصناف: {total}")

        for p in prods:
            p_id = p.get("id")
            col_p_img, col_p_info, col_p_act = st.columns([1, 4, 2])
            with col_p_img:
                show_image(p.get("image_path"))
            with col_p_info:
                st.markdown(f"""<div class="item-card"><p style="margin:0; font-size:18px; font-weight:bold;">🍽️ {p.get('item_name')}</p>
                <p style="margin:5px 0 0 0; color:#333333;">الكمية: <b>{p.get('quantity','1')} {p.get('unit','')}</b> | السعر: <b>{p.get('price')} د.أ</b></p></div>""",
                            unsafe_allow_html=True)
            with col_p_act:
                with st.popover("✏️ تعديل"):
                    n_name = st.text_input("الاسم", value=p.get("item_name") or "", key=f"en_{p_id}")
                    n_price = st.number_input("السعر", min_value=0.0, value=float(p.get("price") or 0), step=0.25, key=f"ep_{p_id}")
                    n_img = st.file_uploader("صورة جديدة", type=["jpg", "png", "jpeg"], key=f"ei_{p_id}")
                    if st.button("حفظ", key=f"es_{p_id}"):
                        upd = {"item_name": n_name.strip(), "price": n_price}
                        if n_img is not None:
                            upd["image_path"] = image_from_upload(n_img, m_name, f"{p_id}")
                        sb.table("products").update(upd).eq("id", p_id).execute()
                        st.rerun()
                if st.button("🗑️ حذف", key=f"del_item_{p_id}"):
                    sb.table("products").delete().eq("id", p_id).execute()
                    st.rerun()

        if pages > 1:
            g1, g2, g3 = st.columns([1, 2, 1])
            with g1:
                if page > 0 and st.button("◀ السابق", key="m_prev"):
                    st.session_state.m_prod_page = page - 1
                    st.rerun()
            with g2:
                st.markdown(f"<div style='text-align:center'>صفحة {page + 1} من {pages}</div>", unsafe_allow_html=True)
            with g3:
                if page < pages - 1 and st.button("التالي ▶", key="m_next"):
                    st.session_state.m_prod_page = page + 1
                    st.rerun()
        st.session_state.m_prod_page = page

    # ---------------- العروض ----------------
    with tab2:
        st.subheader("🏷️ إضافة عروض وخصومات خاصة بمتجرك")
        with st.form("merchant_offer_form"):
            off_title = st.text_input("عنوان العرض")
            off_desc = st.text_area("تفاصيل العرض والشروط")
            off_date = st.text_input("ساري لغاية تاريخ", "2026-12-31")
            sub_off = st.form_submit_button("نشر العرض")
        if sub_off and off_title:
            try:
                sb.table("offers").insert({"merchant_name": m_name, "title": off_title,
                                           "discount_details": off_desc, "valid_until": off_date}).execute()
                st.success("تم نشر العرض بنجاح!")
            except Exception as e:
                st.error(f"خطأ أثناء نشر العرض: {e}")

    # ---------------- الطلبات ----------------
    with tab3:
        st.subheader("📦 طلبات المتجر الواردة (خصم العمولة 10%)")
        if not merchant_orders:
            st.info("لا توجد طلبات واردة لمتجرك حتى الآن.")
        for ord_item in merchant_orders:
            o_id = ord_item.get("id")
            o_stat = ord_item.get("order_status", "قيد التجهيز")
            o_dname = ord_item.get("driver_name", "")
            o_odet = ord_item.get("order_details", "")

            merchant_items_total = 0.0
            for line in o_odet.split("\n"):
                if tag in line:
                    match = re.search(r"\((\d+(\.\d+)?) د\.أ\)", line)
                    if match:
                        merchant_items_total += float(match.group(1))
            commission_fee = merchant_items_total * COMMISSION
            net_amount = merchant_items_total - commission_fee

            driver_text = "في انتظار تعيين سائق وتوجهه للمتجر"
            if o_dname:
                driver_text = (f"✅ استلم الكابتن ({o_dname}) الطلب وتم تسليمه للزبون." if o_stat == "تم التوصيل"
                               else f"🛵 الكابتن ({o_dname}) يتابع الطلب حالياً.")

            # لا نعرض للتاجر سطور المتاجر الأخرى ولا بيانات الزبون
            own_lines = "\n".join(l for l in o_odet.split("\n") if tag in l)
            st.markdown(f"""
            <div class="merchant-card">
                <h4>🛒 طلب رقم #{o_id}</h4>
                <p><b>🕒 الوقت:</b> {ord_item.get('created_at','')} | <b>📌 الحالة:</b> {o_stat}</p>
                <p><b>🚚 السائق:</b> <span style="color:#D84315; font-weight:bold;">{driver_text}</span></p>
                <p><b>إجمالي أصناف متجرك:</b> {merchant_items_total:.2f} د.أ | <span style="color:#C62828;"><b>العمولة (10%):</b> {commission_fee:.2f} د.أ</span> | <b>الصافي:</b> {net_amount:.2f} د.أ</p>
                <hr style="border: 0.5px solid #ddd;">
                <pre style="background-color:#F9F9F9; padding:10px; border-radius:5px; color:#000; border:1px solid #ddd; white-space:pre-wrap;">{own_lines}</pre>
            </div>""", unsafe_allow_html=True)

            if o_stat == "قيد التجهيز":
                if st.button(f"✨ تأكيد جاهزية الطلب رقم #{o_id}", key=f"ready_ord_{o_id}"):
                    sb.table("orders").update({"order_status": "جاهز للاستلام"}).eq("id", o_id).execute()
                    if PUSH_ON:      # تنبيه السائق المعيّن (إن وُجد) والإدارة بأن الطلب جاهز
                        try:
                            if o_dname:
                                d = sb.table("drivers").select("id").eq("name", o_dname).limit(1).execute().data or []
                                if d:
                                    send_push("driver", d[0]["id"], "Halago", f"الطلب #{o_id} جاهز للاستلام من {m_name}")
                            send_push("admin", 0, "Halago", f"الطلب #{o_id} جاهز للاستلام من {m_name}")
                        except Exception:
                            pass
                    st.success("تم تحديث حالة الطلب بأنه جاهز للاستلام!")
                    st.rerun()
            st.markdown("---")

    # ---------------- تعديل المتجر ----------------
    with tab4:
        st.subheader("⚙️ تعديل بيانات ومعلومات وصورة المتجر")
        with st.form("edit_merchant_form"):
            edit_name = st.text_input("اسم المتجر", value=m_name)
            cur_cat = m_data.get("category") if m_data.get("category") in CATEGORIES else CATEGORIES[0]
            edit_cat = st.selectbox("التصنيف الرئيسي", CATEGORIES, index=CATEGORIES.index(cur_cat))
            edit_phone = st.text_input("رقم الهاتف", value=m_data.get("phone", ""))
            edit_loc = st.text_input("العنوان ووصف الموقع", value=m_data.get("location", ""))
            edit_map = st.text_input("رابط موقع المتجر على خرائط جوجل", value=m_data.get("map_link", "") or "")
            st.markdown("### 📷 تحديث صورة المتجر الرئيسية")
            edit_img_file = st.file_uploader("اختر صورة جديدة للمتجر (JPG, PNG)", type=["jpg", "png", "jpeg"])
            submit_edit = st.form_submit_button("💾 حفظ وتحديث بيانات المتجر")
        if submit_edit:
            if not valid_phone(edit_phone):
                st.error("رقم الهاتف غير صحيح.")
            else:
                try:
                    upd = {"name": edit_name.strip(), "category": edit_cat, "phone": norm_phone(edit_phone),
                           "location": edit_loc.strip(), "map_link": edit_map.strip()}
                    if edit_img_file is not None:
                        upd["image_data"] = image_from_upload(edit_img_file, edit_name.strip(), "logo")
                    xy = coords_from_map_link(edit_map.strip()) if (coords_from_map_link and edit_map.strip()) else None
                    if xy:
                        upd["lat"], upd["lng"] = xy
                    try:
                        sb.table("merchants").update(upd).eq("id", m_id).execute()
                    except Exception:
                        upd.pop("lat", None)
                        upd.pop("lng", None)
                        sb.table("merchants").update(upd).eq("id", m_id).execute()
                    st.success("تم تحديث بيانات وصورة المتجر بنجاح!")
                    st.rerun()
                except Exception as e:
                    st.error(f"خطأ أثناء تحديث البيانات: {e}")

        with st.expander("🔐 تغيير رمز PIN"):
            with st.form("m_pin_change"):
                old_pin = st.text_input("PIN الحالي", type="password", max_chars=4)
                new_pin = st.text_input("PIN الجديد (4 أرقام)", type="password", max_chars=4)
                go_pin = st.form_submit_button("تغيير PIN")
            if go_pin:
                ok, msg = check_pin(sb, "merchants", m_data, old_pin)
                if not ok:
                    st.error(msg if msg != NO_PIN else "لا يوجد PIN حالي.")
                elif not valid_pin(new_pin):
                    st.error("PIN الجديد يجب أن يكون 4 أرقام.")
                else:
                    set_pin(sb, "merchants", m_id, m_data.get("phone"), new_pin)
                    st.success("تم تغيير PIN.")
