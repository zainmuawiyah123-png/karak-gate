# شغّله مرة واحدة فقط:  python generate_vapid.py
# يولّد مفاتيح VAPID مجانًا. احفظ المفتاح الخاص سرًا (st.secrets أو متغير بيئة) ولا ترفعه لأي مكان عام.
import base64
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization

b64 = lambda b: base64.urlsafe_b64encode(b).rstrip(b"=").decode()
key = ec.generate_private_key(ec.SECP256R1())
private = key.private_numbers().private_value.to_bytes(32, "big")
public = key.public_key().public_bytes(
    serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
)
print("VAPID_PRIVATE_KEY =", b64(private), " <-- سري، للسيرفر فقط")
print("VAPID_PUBLIC_KEY  =", b64(public), " <-- يوضع في shell/app.js")
