import streamlit as st
from supabase import create_client

# ============================================================
# إعداد صفحة الزبون
# ============================================================
st.set_page_config(
    page_title="بوابة الكرك - Karak Gate",
    page_icon="🛒",
    layout="wide"
)

# ============================================================
# الاتصال بقاعدة البيانات (Supabase)
# ============================================================
SUPABASE_URL = "https://tzkdxodvlzggmcntnqer.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InR6a2R4b2R2bHpnZ21jbnRucWVyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTA5MzM3MzksImV4cCI6MjEwNjUwOTczOX0.M944yHglTXVyPrxySSQj0MBaqpr2I_8ub7Uoofbd2_4"

try:
    if "SUPABASE_ANON_KEY" in st.secrets:
        SUPABASE_ANON_KEY = str(st.secrets["SUPABASE_ANON_KEY"]).strip()
except Exception:
    pass

@st.cache_resource
def init_db():
    return create_client(SUPABASE_URL.strip(), SUPABASE_ANON_KEY.strip())

sb = init_db()

# ============================================================
# تصميم الواجهة الرئيسية للزبون
# ============================================================
st.title("🛒 بوابة الكرك الشاملة")
st.caption("اطلب احتياجاتك من أفضل المتاجر في الكرك بكل سهولة")

st.markdown("---")

# جلب المتاجر مباشرة بدون شروط معقدة لتظهر فور إضافتها
try:
    merchants_res = sb.table("merchants").select("*").execute()
    merchants_list = merchants_res.data if merchants_res.data else []
except Exception as e:
    merchants_list = []
    st.error(f"خطأ في الاتصال بقاعدة البيانات: {e}")

if merchants_list:
    st.subheader("🏬 المتاجر المتاحة")
    
    # عرض المتاجر في أعمدة جميلة
    cols = st.columns(3)
    for idx, merchant in enumerate(merchants_list):
        m_name = merchant.get("name", "متجر")
        m_cat = merchant.get("category", "")
        m_loc = merchant.get("location", "")
        m_phone = merchant.get("phone", "")
        m_img = merchant.get("image_data") or "https://images.unsplash.com/photo-1542838132-92c53300491e?auto=format&fit=crop&w=400&q=80"
        m_map = merchant.get("map_link", "")

        with cols[idx % 3]:
            st.image(m_img, use_container_width=True)
            st.markdown(f"### {m_name}")
            st.write(f"📂 التصنيف: **{m_cat}**")
            st.write(f"📍 الموقع: {m_loc}")
            st.write(f"📞 الهاتف: {m_phone}")
            
            if m_map:
                st.markdown(f'<a href="{m_map}" target="_blank">🗺 فتح الموقع على الخريطة</a>', unsafe_allow_html=True)
            
            st.markdown("---")
else:
    st.info("جاري إضافة المتاجر قريباً... ترقبونا!")
