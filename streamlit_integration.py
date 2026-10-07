"""أجزاء الدمج مع تطبيقاتك (Supabase).
الخصوصية: الزبون لا يُرسل ولا يستقبل أي إشعار، ونص الإشعار لا يحتوي بيانات الزبون.
مسار الطلب: الزبون ← الإدارة ← (زر) التاجر ← (تعيين) السائق.
(أزرار الإدارة جاهزة داخل app_admin_updated.py المرفق؛ هنا فقط ما تحتاجه التطبيقات الأخرى.)
"""
import streamlit as st
from push_service import decode_sub, save_subscription


# في تطبيق التاجر: داخل فرع dashboard بعد تحديد m_id:   capture_subscription("merchant", m_id)
# في تطبيق السائق: بعد تسجيل الدخول:                      capture_subscription("driver", driver_id)
def capture_subscription(role, owner_key):
    sub = st.query_params.get("sub")
    flag = f"push_saved_{role}_{owner_key}"
    if sub and not st.session_state.get(flag):
        try:
            save_subscription(role, owner_key, decode_sub(sub))
            st.session_state[flag] = True
        except Exception:
            pass
