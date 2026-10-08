-- شغّله مرة واحدة: Supabase > SQL Editor > New query > Run

-- 1) تقييمات الزبائن للمتاجر (تقييم واحد لكل متجر في كل طلب)
create table if not exists store_ratings (
  id bigserial primary key,
  merchant_name text not null,
  customer_phone text not null,
  order_id bigint,
  stars integer not null check (stars between 1 and 5),
  comment text,
  created_at timestamptz default now(),
  unique (merchant_name, customer_phone, order_id)
);
create index if not exists store_ratings_merchant on store_ratings(merchant_name);

-- 2) الإعلانات المتحركة في الصفحة الرئيسية (تديرها الإدارة)
create table if not exists ads (
  id bigserial primary key,
  tag text,
  title text not null,
  subtitle text,
  color text default 'purple',     -- purple / orange / green / blue
  active boolean default true,
  sort integer default 0,
  created_at timestamptz default now()
);
