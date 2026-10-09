"""اتصال Supabase للخدمات الجديدة (الإشعارات والإعدادات).
ضع في Secrets لكل تطبيق (Streamlit Cloud > Settings > Secrets):
  SUPABASE_URL = "https://xxxx.supabase.co"
  SUPABASE_SERVICE_KEY = "مفتاح service_role"    # سري جدًا: لا تضعه في الكود ولا على GitHub
  VAPID_PRIVATE_KEY = "..."
  VAPID_EMAIL = "mailto:بريدك@example.com"
"""
import os
import streamlit as st
from supabase import create_client


def _secret(name, default=""):
    try:
        # أولاً: فحص متغيرات البيئة في ريندر (Render)
        val = os.getenv(name)
        if val:
            return str(val).strip()
        
        # ثانياً: إذا لم توجد، فحص st.secrets محلياً
        if name in st.secrets:
            return str(st.secrets[name]).strip()
    except Exception:
        pass
    return default


@st.cache_resource
def get_sb():
    url = _secret("SUPABASE_URL")
    key = _secret("SUPABASE_SERVICE_KEY")
    if not url or not key:
        st.error("أضف SUPABASE_URL و SUPABASE_SERVICE_KEY في متغيرات البيئة في Render أو في Secrets.")
        st.stop()
    return create_client(url, key)
