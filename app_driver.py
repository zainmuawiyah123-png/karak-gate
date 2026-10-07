"""عرض الطلب للسائق: خريطة بين التاجر والزبون + المسافة + الأجرة + زر الملاحة.
مجاني بالكامل: pydeck (مدمج مع Streamlit) + OSRM العام للمسافة على الطرق.
الأجرة تتحكم بها الإدارة من settings_service.render_fee_settings_admin(). عدّل أسماء الحقول (order["..."]) لتطابق قاعدتك.
"""
import math
import requests
import streamlit as st
import pydeck as pdk

from settings_service import calc_fee   # الأجرة تُقرأ من إعدادات الإدارة

def haversine_km(lat1, lon1, lat2, lon2):
    """مسافة خط مستقيم بالكيلومتر."""
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


@st.cache_data(ttl=3600, show_spinner=False)
def route_info(lat1, lon1, lat2, lon2):
    """مسافة ومدة ومسار القيادة الفعلي. إذا فشلت الخدمة نرجع تقديرًا من الخط المستقيم."""
    url = (f"https://router.project-osrm.org/route/v1/driving/"
           f"{lon1},{lat1};{lon2},{lat2}?overview=full&geometries=geojson")
    try:
        r = requests.get(url, timeout=6).json()
        rt = r["routes"][0]
        return {"km": rt["distance"] / 1000, "min": rt["duration"] / 60,
                "path": rt["geometry"]["coordinates"], "estimated": False}
    except Exception:
        km = haversine_km(lat1, lon1, lat2, lon2) * 1.3   # معامل تقريبي لتعرج الطرق
        return {"km": km, "min": km / 30 * 60,
                "path": [[lon1, lat1], [lon2, lat2]], "estimated": True}


def render_driver_order(order, merchant):
    """استدعها داخل صفحة السائق للطلب المعيّن له فقط.
    order: dict فيه id, cust_lat, cust_lon   |   merchant: dict فيه name, lat, lon
    """
    m_lat, m_lon = merchant["lat"], merchant["lon"]
    c_lat, c_lon = order["cust_lat"], order["cust_lon"]
    info = route_info(m_lat, m_lon, c_lat, c_lon)
    fee = calc_fee(info["km"])

    st.subheader(f"طلب #{order['id']}")
    a, b, c = st.columns(3)
    a.metric("المسافة", f"{info['km']:.1f} كم")
    b.metric("الوقت التقريبي", f"{info['min']:.0f} دقيقة")
    c.metric("أجرتك", f"{fee:.2f} د.أ")
    if info["estimated"]:
        st.caption("المسافة تقديرية (تعذّر حساب مسار الطريق الآن).")

    pts = [
        {"name": f"التاجر: {merchant['name']}", "lon": m_lon, "lat": m_lat, "color": [232, 64, 47]},
        {"name": "الزبون", "lon": c_lon, "lat": c_lat, "color": [30, 120, 220]},
    ]
    layers = [
        pdk.Layer("PathLayer", [{"path": info["path"]}], get_path="path",
                  get_color=[40, 40, 40], width_min_pixels=4),
        pdk.Layer("ScatterplotLayer", pts, get_position="[lon, lat]", get_fill_color="color",
                  get_radius=60, radius_min_pixels=9, pickable=True),
    ]
    view = pdk.ViewState(latitude=(m_lat + c_lat) / 2, longitude=(m_lon + c_lon) / 2,
                         zoom=12.5 if info["km"] < 5 else 11)
    st.pydeck_chart(pdk.Deck(layers=layers, initial_view_state=view,
                             tooltip={"text": "{name}"}), use_container_width=True)

    # ملاحة جوجل: من موقع السائق الحالي ← التاجر ← الزبون (تفتح تطبيق الخرائط)
    nav = (f"https://www.google.com/maps/dir/?api=1&destination={c_lat},{c_lon}"
           f"&waypoints={m_lat},{m_lon}&travelmode=driving")
    st.link_button("🧭 ابدأ الملاحة", nav, use_container_width=True)
    return fee
