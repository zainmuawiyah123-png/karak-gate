import streamlit as st
from datetime import datetime
import json
import os

# إعدادات الصفحة
st.set_page_config(
    page_title="بوابة الكرك - Karak Gate",
    page_icon="🛒",
    layout="wide"
)

# محاكاة قاعدة بيانات محلية (ملف JSON) لحفظ البيانات مؤقتاً في حال عدم توفر Supabase
DATA_FILE = "karak_gate_data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "products": [
            {"id": 1, "name": "منسف كركي أصلي (لحم شهي)", "price": 15.0, "category": "طعام", "image": "🍖"},
            {"id": 2, "name": "جميد كركي فاخر (حبة)", "price": 8.5, "category": "منتجات محلية", "image": "🏺"},
            {"id": 3, "name": "سمن بلدي كركي (كيلو)", "price": 12.0, "category": "منتجات محلية", "image": "🧈"},
            {"id": 4, "name": "زعتر كركي جبلي", "price": 4.0, "category": "بهارات", "image": "🌿"}
        ],
        "orders": [],
        "delivery_fees": {
            "الكرك": 2.0,
            "عمان": 4.0,
            "إربد": 5.0,
            "الزرقاء": 4.0,
            "العقبة": 6.0,
            "مأدبا": 3.0,
            "معان": 5.0,
            "الطفيلة": 3.0,
            "عجلون": 5.0,
            "جرش": 5.0,
            "المفرق": 5.0,
            "السلط / البحر الميت": 3.5
        },
        "settings": {
            "default_delivery": 3.0
        }
    }

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

if "db" not in st.session_state:
    st.session_state.db = load_data()

db = st.session_state.db

# تهيئة عربة التسوق
if "cart" not in st.session_state:
    st.session_state.cart = []

if "user" not in st.session_state:
    st.session_state.user = {
        "name": "",
        "phone": "",
        "city": "الكرك",
        "address": ""
    }

# القائمة الجانبية للتنقل
st.sidebar.title("🛒 بوابة الكرك")
st.sidebar.markdown("---")
menu = st.sidebar.radio("اختر القسم:", ["الرئيسية (التسوق)", "عربة التسوق والدفع", "تتبع الطلبات", "لوحة إدارة أجور التوصيل"])

# 1. الرئيسية (التسوق)
if menu == "الرئيسية (التسوق)":
    st.title("🌟 مرحباً بك في بوابة الكرك للتسوق")
    st.write("أصالة التراث الكركي، منتجات محلية وطعام بيتي فاخر يصلك أينما كنت في المملكة.")
    
    # تصفية المنتجات
    categories = ["الكل"] + list(set(p["category"] for p in db["products"]))
    selected_cat = st.selectbox("تصنيف المنتجات:", categories)
    
    col1, col2, col3, col4 = st.columns(4)
    for i, product in enumerate(db["products"]):
        if selected_cat != "الكل" and product["category"] != selected_cat:
            continue
        with [col1, col2, col3, col4][i % 4]:
            st.markdown(f"### {product['image']} {product['name']}")
            st.write(**السعر:** {product['price']} دينار)
            if st.button(f"أضف للسلة 🛒", key=f"prod_{product['id']}"):
                st.session_state.cart.append(product)
                st.success(f"تمت إضافة {product['name']} إلى السلة!")

# 2. عربة التسوق والدفع
elif menu == "عربة التسوق والدفع":
    st.title("🛒 عربة التسوق وإتمام الطلب")
    
    if not st.session_state.cart:
        st.info("عربة التسوق فارغة حالياً. تصفح المنتجات وأضف ما يعجبك!")
    else:
        total_price = 0
        for idx, item in enumerate(st.session_state.cart):
            col_a, col_b, col_c = st.columns([3, 1, 1])
            col_a.write(f"{item['image']} {item['name']}")
            col_b.write(f"{item['price']} د.أ")
            if col_c.button("حذف", key=f"del_{idx}"):
                st.session_state.cart.pop(idx)
                st.rerun()
            total_price += item['price']
        
        st.markdown("---")
        st.subheader("📍 معلومات التوصيل")
        
        # إدخال بيانات العميل وتشمل المحافظات المفتوحة
        c_name = st.text_input("الاسم الكامل", value=st.session_state.user["name"])
        c_phone = st.text_input("رقم الهاتف", value=st.session_state.user["phone"])
        
        cities = list(db["delivery_fees"].keys())
        current_city = st.session_state.user["city"]
        if current_city not in cities:
            cities.append(current_city)
            
        c_city = st.selectbox("المحافظة / المدينة", cities, index=cities.index(current_city) if current_city in cities else 0)
        c_address = st.text_area("تفاصيل العنوان (المنطقة، الشارع، رقم البناية)", value=st.session_state.user["address"])
        
        # حساب أجور التوصيل بناءً على ما تحدده الإدارة
        delivery_fee = db["delivery_fees"].get(c_city, db["settings"]["default_delivery"])
        
        st.info(f"🚚 أجور التوصيل لمنطقة ({c_city}): **{delivery_fee} دينار**")
        st.markdown(f"### الإجمالي النهائي: **{total_price + delivery_fee} دينار** (شامل التوصيل)")
        
        if st.button("إتمام الطلب وتأكيده 🚀", type="primary"):
            if not c_name or not c_phone or not c_address:
                st.error("يرجى تعبثة كافة بيانات الاسم ورقم الهاتف وعنوان التوصيل بدقة.")
            else:
                st.session_state.user = {"name": c_name, "phone": c_phone, "city": c_city, "address": c_address}
                
                new_order = {
                    "order_id": f"KG-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    "customer": st.session_state.user,
                    "items": st.session_state.cart,
                    "subtotal": total_price,
                    "delivery_fee": delivery_fee,
                    "total": total_price + delivery_fee,
                    "status": "قيد المعгляд",
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M")
                }
                
                db["orders"].append(new_order)
                save_data(db)
                st.session_state.cart = []
                st.success(f"تم إرسال طلبك بنجاح! رقم الطلب الخاص بك هو: {new_order['order_id']}")

# 3. تتبع الطلبات
elif menu == " تتبع الطلبات":
    st.title("📦 تتبع الطلبات")
    search_phone = st.text_input("أدخل رقم الهاتف للبحث عن طلباتك:")
    
    if search_phone:
        user_orders = [o for o in db["orders"] if o["customer"]["phone"] == search_phone]
        if not user_orders:
            st.warning("لا توجد طلبات مسجلة بهذا الرقم.")
        else:
            for ord in user_orders:
                with st.expander(f"طلب رقم: {ord['order_id']} - الحالة: {ord['status']}"):
                    st.write(f"**التاريخ:** {ord['date']}")
                    st.write(f"**المدينة:** {ord['customer']['city']} - **العنوان:** {ord['customer']['address']}")
                    st.write(f"**المجموع الكلي:** {ord['total']} د.أ (يتضمن أجور التوصيل: {ord['delivery_fee']} د.أ)")
                    st.write("**المنتجات المطلوبة:**")
                    for itm in ord['items']:
                        st.write(f"- {itm['name']} ({itm['price']} د.أ)")

# 4. لوحة إدارة أجور التوصيل
elif menu == "لوحة إدارة أجور التوصيل":
    st.title("⚙️ لوحة الإدارة - التحكم بأجور التوصيل والمحافظات")
    st.write("من خلال هذه لوحة التحكم، يمكنك تعديل أجور التوصيل لكل محافظة أو إضافة مدينة جديدة بسهولة:")
    
    with st.form("update_delivery_form"):
        updated_fees = {}
        cols = st.columns(2)
        idx = 0
        for city, fee in db["delivery_fees"].items():
            with cols[idx % 2]:
                updated_fees[city] = st.number_input(f"أجور توصيل ({city}) - دينار", value=float(fee), step=0.5, key=f"fee_{city}")
            idx += 1
            
        st.markdown("---")
        st.subheader("إضافة مدينة أو منطقة جديدة")
        new_city_name = st.text_input("اسم المدينة الجديدة")
        new_city_fee = st.number_input("أجور التوصيل للمدينة الجديدة", value=3.0, step=0.5)
        
        submitted = st.form_submit_button("حفظ التحديثات وجدول الأسعار")
        if submitted:
            db["delivery_fees"] = updated_fees
            if new_city_name:
                db["delivery_fees"][new_city_name] = new_city_fee
            save_data(db)
            st.success("تم تحديث جدول أجور التوصيل بنجاح!")
