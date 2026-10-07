"""استيراد أصناف المتاجر الكبيرة بالجملة (آلاف الأصناف) على Supabase.

1) رفع ملف Excel/CSV فيه الأصناف والأسعار والباركود (يصدّره المتجر من برنامج الكاشير/المحاسبة).
2) الصور: تلقائيًا من Open Food Facts بالباركود (مجاني)، أو ملف ZIP صور أسماؤها = الباركود أو اسم الصنف.
تحتاج: pandas, openpyxl, Pillow, requests, supabase  + تشغيل catalog_setup في supabase_setup.sql
"""
import hashlib
import io
import os
import re
import time
import zipfile

import pandas as pd
import requests
import streamlit as st

BUCKET = "product-images"
CHUNK = 500
UA = {"User-Agent": "KarakGate/1.0 (product image lookup)"}

ALIASES = {
    "item_name": ["item_name", "name", "اسم الصنف", "الصنف", "الاسم", "اسم المنتج", "المنتج", "الوصف", "description"],
    "price": ["price", "السعر", "سعر البيع", "سعر"],
    "quantity": ["quantity", "الكمية", "الحجم"],
    "unit": ["unit", "الوحدة"],
    "barcode": ["barcode", "الباركود", "باركود", "رمز الصنف", "رمز", "code", "sku"],
    "image_url": ["image_url", "image", "رابط الصورة", "الصورة", "image_path"],
    "category": ["category", "القسم", "التصنيف", "department"],
}


# ----------------------------------------------------------------- قراءة وتنظيف الملف
def _norm(s):
    return re.sub(r"\s+", " ", str(s or "").strip().lower())


def map_columns(df):
    wanted = {f: {_norm(a) for a in al} for f, al in ALIASES.items()}
    mapping = {}
    for col in df.columns:
        n = _norm(col)
        for field, names in wanted.items():
            if field not in mapping and n in names:
                mapping[field] = col
    return mapping


def clean_barcode(v):
    s = str(v or "").strip()
    if not s:
        return None
    if re.fullmatch(r"\d+(\.\d+)?[eE]\+?\d+", s):          # 6.28E+12 من إكسل
        s = str(int(float(s)))
    if s.endswith(".0"):
        s = s[:-2]
    s = re.sub(r"\D", "", s)
    return s or None


def parse_price(v):
    s = str(v or "").strip().replace(",", ".")
    s = re.sub(r"[^\d.]", "", s)
    try:
        p = float(s)
        return p if p > 0 else None
    except ValueError:
        return None


def parse_catalog(df, merchant):
    """يرجع (rows, issues, mapping)."""
    df = df.fillna("")
    mp = map_columns(df)
    if "item_name" not in mp or "price" not in mp:
        return [], ["لم أجد عمودي (اسم الصنف) و(السعر) في الملف. استخدم القالب المرفق."], mp
    rows, issues, seen, sci = {}, [], 0, 0
    for i, r in df.iterrows():
        line = i + 2
        name = str(r[mp["item_name"]]).strip()
        price = parse_price(r[mp["price"]])
        if not name:
            continue
        if price is None:
            issues.append(f"سطر {line}: سعر غير صحيح للصنف «{name}» (تم تجاهله)")
            continue
        row = {"merchant_name": merchant, "item_name": name, "price": price,
               "quantity": (str(r[mp["quantity"]]).strip() if "quantity" in mp else "") or "1",
               "unit": (str(r[mp["unit"]]).strip() if "unit" in mp else "") or "حبة"}
        raw_bc = str(r[mp["barcode"]]).strip() if "barcode" in mp else ""
        if re.fullmatch(r"\d+(\.\d+)?[eE]\+?\d+", raw_bc):
            sci += 1
        bc = clean_barcode(raw_bc) if "barcode" in mp else None
        if bc:
            row["barcode"] = bc
        if "image_url" in mp:
            u = str(r[mp["image_url"]]).strip()
            if u.lower().startswith(("http://", "https://", "data:image")):
                row["image_path"] = u
        if "category" in mp:
            c = str(r[mp["category"]]).strip()
            if c:
                row["category"] = c
        key = ("b", bc) if bc else ("n", name)
        if key in rows:
            seen += 1
        rows[key] = row
    if sci:
        issues.append(f"{sci} باركود بصيغة علمية (6.29E+12): إكسل أفسد أرقامها. اجعل عمود الباركود نصًّا (Text) ثم أعد التصدير.")
    if seen:
        issues.append(f"{seen} صنف مكرر داخل الملف (اعتُمد آخر ظهور لكل صنف)")
    return list(rows.values()), issues, mp


def read_table(f):
    name = f.name.lower()
    if name.endswith(".csv"):
        raw = f.getvalue()
        for enc in ("utf-8-sig", "cp1256"):
            try:
                return pd.read_csv(io.BytesIO(raw), dtype=str, encoding=enc).fillna("")
            except UnicodeDecodeError:
                continue
    return pd.read_excel(f, dtype=str).fillna("")


def template_bytes():
    df = pd.DataFrame([
        {"اسم الصنف": "حليب كامل الدسم 1 لتر", "السعر": 1.10, "الكمية": 1, "الوحدة": "عبوة",
         "الباركود": "6291003012345", "رابط الصورة": "", "القسم": "ألبان"},
        {"اسم الصنف": "أرز مصري 1 كغ", "السعر": 1.50, "الكمية": 1, "الوحدة": "كيس",
         "الباركود": "6291003067890", "رابط الصورة": "", "القسم": "مواد تموينية"},
    ])
    buf = io.BytesIO()
    df.to_excel(buf, index=False)
    return buf.getvalue()


# ----------------------------------------------------------------- الرفع إلى Supabase
def _existing_names(sb, merchant):
    names, start = set(), 0
    while True:
        d = (sb.table("products").select("item_name").eq("merchant_name", merchant)
             .range(start, start + 999).execute().data or [])
        names.update(x["item_name"] for x in d)
        if len(d) < 1000:
            return names
        start += 1000


def _groups(rows):
    """مجموعات متجانسة بالمفاتيح (شرط الإدخال الجماعي) ثم دفعات من CHUNK."""
    by_keys = {}
    for r in rows:
        by_keys.setdefault(tuple(sorted(r)), []).append(r)
    for grp in by_keys.values():
        for i in range(0, len(grp), CHUNK):
            yield grp[i:i + CHUNK]


def import_rows(sb, merchant, rows, update_existing=True, progress=None):
    stats = {"inserted": 0, "upserted": 0, "skipped": 0, "errors": []}
    with_bc = [r for r in rows if r.get("barcode")]
    no_bc = [r for r in rows if not r.get("barcode")]
    existing = _existing_names(sb, merchant) if no_bc else set()
    fresh = [r for r in no_bc if r["item_name"] not in existing]
    stats["skipped"] += len(no_bc) - len(fresh)
    total, done = len(with_bc) + len(fresh), 0

    for chunk in _groups(with_bc):
        try:
            sb.table("products").upsert(chunk, on_conflict="merchant_name,barcode",
                                        ignore_duplicates=not update_existing).execute()
            stats["upserted"] += len(chunk)
        except Exception as e:
            stats["errors"].append(str(e))
        done += len(chunk)
        if progress:
            progress(done / max(total, 1))
    for chunk in _groups(fresh):
        try:
            sb.table("products").insert(chunk).execute()
            stats["inserted"] += len(chunk)
        except Exception as e:
            stats["errors"].append(str(e))
        done += len(chunk)
        if progress:
            progress(done / max(total, 1))
    return stats


# ----------------------------------------------------------------- الصور
def fetch_off_image(barcode):
    try:
        r = requests.get(f"https://world.openfoodfacts.org/api/v2/product/{barcode}.json",
                         params={"fields": "image_front_url,image_front_small_url"}, headers=UA, timeout=8)
        if r.ok:
            p = r.json().get("product") or {}
            return p.get("image_front_url") or p.get("image_front_small_url")
    except Exception:
        pass
    return None


def fill_images_from_off(sb, merchant, limit, progress=None):
    rows = (sb.table("products").select("id,barcode").eq("merchant_name", merchant)
            .is_("image_path", "null").is_("img_tried", "null").not_.is_("barcode", "null")
            .limit(limit).execute().data or [])
    found = 0
    for n, r in enumerate(rows, 1):
        bc = str(r.get("barcode") or "")
        url = fetch_off_image(bc) if len(bc) >= 8 else None
        upd = {"img_tried": True}
        if url:
            upd["image_path"] = url
            found += 1
        sb.table("products").update(upd).eq("id", r["id"]).execute()
        if progress:
            progress(n / len(rows))
        time.sleep(0.7)          # حد Open Food Facts ≈ 100 طلب/دقيقة
    return len(rows), found


def _prep_image(data):
    from PIL import Image
    im = Image.open(io.BytesIO(data)).convert("RGB")
    im.thumbnail((600, 600))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=80, optimize=True)
    return buf.getvalue()


def _zip_image_names(zf):
    return [n for n in zf.namelist()
            if n.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))
            and not n.startswith("__MACOSX") and not os.path.basename(n).startswith(".")]


def process_zip_batch(sb, storage_sb, merchant, zip_bytes, start, count, progress=None):
    zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
    names = _zip_image_names(zf)
    mh = hashlib.md5(merchant.encode()).hexdigest()[:8]
    ok = miss = 0
    errs = []
    batch = names[start:start + count]
    for k, n in enumerate(batch, 1):
        stem = os.path.splitext(os.path.basename(n))[0].strip()
        is_bc = bool(re.fullmatch(r"\d{6,}", stem))
        try:
            img = _prep_image(zf.read(n))
            key = stem if is_bc else hashlib.md5(stem.encode()).hexdigest()[:16]
            path = f"{mh}/{key}.jpg"
            storage_sb.storage.from_(BUCKET).upload(path, img, {"content-type": "image/jpeg", "upsert": "true"})
            url = storage_sb.storage.from_(BUCKET).get_public_url(path)
            q = sb.table("products").update({"image_path": url, "img_tried": True}).eq("merchant_name", merchant)
            q = q.eq("barcode", stem) if is_bc else q.eq("item_name", stem)
            if q.execute().data:
                ok += 1
            else:
                miss += 1
        except Exception as e:
            errs.append(f"{n}: {e}")
        if progress:
            progress(k / len(batch))
    return ok, miss, errs, len(names)


# ----------------------------------------------------------------- الواجهة
def render_bulk_import(sb, merchant_names, storage_sb=None, fixed_merchant=None):
    """للإدارة: render_bulk_import(sb, أسماء_المتاجر, storage_sb)  |  للتاجر: fixed_merchant=اسم متجره"""
    st.subheader("📥 استيراد الأصناف بالجملة")
    merchant = fixed_merchant or st.selectbox("المتجر:", merchant_names, key="bulk_merchant")
    t1, t2 = st.tabs(["1️⃣ الأصناف والأسعار (Excel / CSV)", "2️⃣ الصور"])

    with t1:
        st.markdown("اطلب من المتجر **تصدير قائمة الأصناف من برنامج الكاشير** (اسم، سعر، باركود) بصيغة Excel أو CSV. "
                    "الأعمدة المطلوبة: **اسم الصنف** و**السعر**، والباقي اختياري (الباركود مهم لتحديث الأسعار لاحقًا وجلب الصور).")
        st.download_button("⬇️ تنزيل قالب Excel", template_bytes(), "قالب_الأصناف.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        f = st.file_uploader("ارفع الملف", type=["xlsx", "csv"], key="bulk_file")
        update_existing = st.checkbox("تحديث أسعار وبيانات الأصناف الموجودة (حسب الباركود)", value=True, key="bulk_upd")
        if f:
            try:
                df = read_table(f)
                rows, issues, mp = parse_catalog(df, merchant)
            except Exception as e:
                st.error(f"تعذّرت قراءة الملف: {e}")
                rows, issues, mp = [], [], {}
            if mp:
                st.caption("الأعمدة التي تعرّفت عليها: " + "، ".join(f"{k} ← {v}" for k, v in mp.items()))
            for msg in issues[:30]:
                st.warning(msg)
            if rows:
                st.success(f"جاهز للاستيراد: {len(rows)} صنف")
                st.dataframe(pd.DataFrame(rows).head(20), use_container_width=True)
                if st.button(f"🚀 ابدأ استيراد {len(rows)} صنف إلى «{merchant}»", key="bulk_go"):
                    bar = st.progress(0.0)
                    s = import_rows(sb, merchant, rows, update_existing, bar.progress)
                    st.success(f"تمت المعالجة: جديد {s['inserted']} | تحديث/إدراج بالباركود {s['upserted']} | موجود مسبقًا وتم تخطيه {s['skipped']}")
                    for e in s["errors"][:5]:
                        st.error(e)
                    if s["errors"]:
                        st.info("إن كان الخطأ عن عمود غير موجود (barcode / category) فشغّل قسم الأصناف في supabase_setup.sql أولًا.")

    with t2:
        st.markdown("##### أ) جلب الصور تلقائيًا بالباركود (مجاني - Open Food Facts)")
        st.caption("تغطي المنتجات المعلّبة والمعروفة فقط، ولا تغطي الخضار واللحوم والمنتجات المحلية. "
                   "الصور من قاعدة بيانات مفتوحة بترخيص CC-BY-SA.")
        lim = st.slider("عدد الأصناف في كل دفعة", 20, 150, 60, 10, key="off_lim")
        if st.button("🖼️ جلب دفعة صور", key="off_go"):
            bar = st.progress(0.0)
            tried, found = fill_images_from_off(sb, merchant, lim, bar.progress)
            if tried == 0:
                st.info("لا توجد أصناف بباركود وبلا صورة بانتظار الجلب.")
            else:
                st.success(f"فُحص {tried} صنف، وُجدت صور لـ {found}. كرّر الضغط للدفعة التالية.")

        st.markdown("---")
        st.markdown("##### ب) رفع ملف ZIP للصور")
        st.caption("اسم كل صورة = باركود الصنف (مثل 6291003012345.jpg) أو اسم الصنف تمامًا كما في القائمة. "
                   "تُصغَّر الصور تلقائيًا وتُخزَّن في Supabase Storage.")
        if storage_sb is None:
            st.info("لرفع الصور أضف SUPABASE_SERVICE_KEY في Secrets وأنشئ الـ bucket (موجود في supabase_setup.sql).")
        else:
            z = st.file_uploader("ملف ZIP", type=["zip"], key="bulk_zip")
            if z:
                if st.session_state.get("bulk_zip_name") != z.name:
                    st.session_state["bulk_zip_name"] = z.name
                    st.session_state["bulk_zip_pos"] = 0
                    st.session_state["bulk_zip_bytes"] = z.getvalue()
                size = st.slider("عدد الصور في كل دفعة", 20, 200, 80, 10, key="zip_batch")
                pos = st.session_state.get("bulk_zip_pos", 0)
                total = len(_zip_image_names(zipfile.ZipFile(io.BytesIO(st.session_state["bulk_zip_bytes"]))))
                st.write(f"تمت معالجة {min(pos, total)} من {total} صورة")
                if pos < total and st.button("⏭️ معالجة الدفعة التالية", key="zip_go"):
                    bar = st.progress(0.0)
                    ok, miss, errs, _ = process_zip_batch(sb, storage_sb, merchant,
                                                          st.session_state["bulk_zip_bytes"], pos, size, bar.progress)
                    st.session_state["bulk_zip_pos"] = pos + size
                    st.success(f"رُبطت {ok} صورة بأصنافها، و{miss} صورة بلا صنف مطابق. "
                               f"المجموع الآن: {min(pos + size, total)} من {total}")
                    for e in errs[:5]:
                        st.error(e)
