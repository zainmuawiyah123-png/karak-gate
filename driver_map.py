"""عرض الطلب للسائق: خريطة بين التاجر والزبون + المسافة + الأجرة + زر الملاحة.
مجاني بالكامل: pydeck (مدمج مع Streamlit) + OSRM العام للمسافة على الطرق.
الأجرة: من سجل الطلب (التوصيل: x) أو من إعدادات المتجر (delivery_fee + fee_per_km) التي تحددها الإدارة. عدّل أسماء الحقول (order["..."]) لتطابق قاعدتك.
"""
import math
import requests
import streamlit as st
import pydeck as pdk

from fees import order_delivery_fee, merchant_fee   # أجرة المتجر من جدول merchants

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


import re


def _iframe(src, height=300):
    """st.iframe في الإصدارات الجديدة، وإلا components.v1.iframe (القديم المُهمَل)."""
    if hasattr(st, "iframe"):
        try:
            st.iframe(src, height=height)
            return
        except Exception:
            pass
    st.components.v1.iframe(src, height=height)


def _coords(row, pairs):
    for a, b in pairs:
        try:
            la, lo = float(row[a]), float(row[b])
            if la or lo:
                return la, lo
        except (KeyError, TypeError, ValueError):
            continue
    return None


_PATS = [
    r"@(-?\d+\.\d+),(-?\d+\.\d+)",
    r"!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)",
    r"[?&](?:q|ll|query|destination)=(-?\d+\.\d+)(?:,|%2C)(-?\d+\.\d+)",
    r"center=(-?\d+\.\d+)%2C(-?\d+\.\d+)",
]


def _scan(text):
    for p in _PATS:
        m = re.search(p, text or "")
        if m:
            return float(m.group(1)), float(m.group(2))
    return None


@st.cache_data(ttl=86400, show_spinner=False)
def coords_from_map_link(url):
    """يستخرج الإحداثيات من رابط خرائط جوجل (يتبع الروابط المختصرة). None إن تعذر."""
    if not url:
        return None
    found = _scan(url)
    if found:
        return found
    try:
        r = requests.get(url, timeout=6, allow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})
        return _scan(r.url) or _scan(r.text[:300000])
    except Exception:
        return None


def cust_coords(order):
    """موقع الزبون من الطلب (يقبل cust_lat/cust_lon أو lat/lng)."""
    c = _coords(order, (("cust_lat", "cust_lon"), ("lat", "lng"), ("lat", "lon")))
    if c:
        return c
    # طلبات قديمة بلا lat/lng: رابط الخريطة محفوظ داخل نص العنوان (… | رابط الخريطة: <رابط>)
    m = re.search(r"رابط الخريطة:\s*(\S+)", str(order.get("customer_address") or ""))
    return coords_from_map_link(m.group(1)) if m else None


def merchant_coords(merchant):
    """إحداثيات المتجر: lat/lng إن وُجدت، وإلا من رابط الخرائط map_link."""
    merchant = merchant or {}
    return _coords(merchant, (("lat", "lng"), ("lat", "lon"))) or coords_from_map_link(merchant.get("map_link"))


def fee_for(order, merchant):
    """(الأجرة, معلومات المسار). الأجرة None إن لم تتوفر؛ المسار None إن نقصت الإحداثيات."""
    mc, cc = merchant_coords(merchant), cust_coords(order)
    info = route_info(mc[0], mc[1], cc[0], cc[1]) if (mc and cc) else None
    fee = order.get("driver_fee")
    if fee is None:
        fee = order_delivery_fee(order)
    if fee is None and info and merchant:
        fee = merchant_fee(merchant, info["km"])
    return (None if fee is None else round(float(fee), 2)), info


def render_driver_order(order, merchant, nav="route", show_map=True):
    """خريطة ومسافة وأجرة للطلب.
    nav: "route" (من موقعي ← المتجر ← الزبون) | "store" (للمتجر فقط) | "customer" (للزبون فقط) | None
    show_map=False: يعرض المسافة والأجرة فقط بدون خريطة (للطلبات غير المسندة، لحماية موقع الزبون)
    """
    fee, info = fee_for(order, merchant)
    if info is None:
        if fee is not None:
            st.metric("أجرتك", f"{fee:.2f} د.أ")
        st.warning("موقع المتجر أو الزبون غير محدد لهذا الطلب، تواصل مع الإدارة.")
        return fee
    (m_lat, m_lon), (c_lat, c_lon) = merchant_coords(merchant), cust_coords(order)

    a, b, c = st.columns(3)
    a.metric("المسافة", f"{info['km']:.1f} كم")
    b.metric("الوقت التقريبي", f"{info['min']:.0f} دقيقة")
    c.metric("أجرتك", "—" if fee is None else f"{fee:.2f} د.أ")
    if info["estimated"]:
        st.caption("المسافة تقديرية (تعذّر حساب مسار الطريق الآن).")

    if not show_map:
        return fee

    # خريطة جوجل المضمّنة: مسار من المتجر إلى الزبون (بدون مفتاح API)
    gsrc = f"https://maps.google.com/maps?saddr={m_lat},{m_lon}&daddr={c_lat},{c_lon}&output=embed"
    st.caption("🔴 المتجر ← 🔵 الزبون (المسار على خرائط جوجل)")
    _iframe(gsrc, height=320)

    pts = [
        {"name": f"المتجر: {merchant['name']}", "lon": m_lon, "lat": m_lat, "color": [232, 64, 47]},
        {"name": "موقع الزبون", "lon": c_lon, "lat": c_lat, "color": [30, 120, 220]},
    ]
    layers = [
        pdk.Layer("PathLayer", [{"path": info["path"]}], get_path="path",
                  get_color=[40, 40, 40], width_min_pixels=4),
        pdk.Layer("ScatterplotLayer", pts, get_position="[lon, lat]", get_fill_color="color",
                  get_radius=60, radius_min_pixels=9, pickable=True),
    ]
    view = pdk.ViewState(latitude=(m_lat + c_lat) / 2, longitude=(m_lon + c_lon) / 2,
                         zoom=12.5 if info["km"] < 5 else 11)
    with st.expander("🗺 خريطة بديلة (إن لم تظهر خريطة جوجل)"):
        st.pydeck_chart(pdk.Deck(layers=layers, initial_view_state=view,
                                 tooltip={"text": "{name}"}), use_container_width=True)

    base = "https://www.google.com/maps/dir/?api=1&travelmode=driving"
    if nav == "route":
        st.link_button("🧭 ابدأ الملاحة", f"{base}&destination={c_lat},{c_lon}&waypoints={m_lat},{m_lon}",
                       use_container_width=True)
    elif nav == "store":
        st.link_button("🧭 الملاحة إلى المتجر", f"{base}&destination={m_lat},{m_lon}", use_container_width=True)
    elif nav == "customer":
        st.link_button("🧭 الملاحة إلى الزبون", f"{base}&destination={c_lat},{c_lon}", use_container_width=True)
    return fee
