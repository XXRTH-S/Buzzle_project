-- Buzzle — โครงฐานข้อมูล
-- โหลดอัตโนมัติตอน db container ขึ้นครั้งแรก (docker-entrypoint-initdb.d)

create extension if not exists "pgcrypto";

create table if not exists media (
  id           uuid primary key default gen_random_uuid(),
  owner_id     uuid,
  filename     text not null,
  storage_key  text not null,
  duration_ms  int,
  language     text default 'auto',          -- 'th' | 'en' | 'auto'
  status       text not null default 'uploaded',
  -- uploaded | normalizing | transcribing | joining | summarizing | done | failed
  error        text,
  asr_backend  text not null default 'scribe',
  summary_template text not null default 'key_points',
  created_at   timestamptz not null default now(),
  delete_after timestamptz                   -- นโยบายลบตาม PDPA
);

create table if not exists segments (
  id          bigserial primary key,
  media_id    uuid not null references media(id) on delete cascade,
  idx         int  not null,
  start_ms    int  not null,
  end_ms      int  not null,
  speaker     text,                          -- SPK_00 ...
  text_model  text not null,                 -- ฉบับที่โมเดลถอด แตะไม่ได้
  text_edited text,                          -- ฉบับที่คนแก้ (null = ยังไม่แก้)
  confidence  real,
  unique (media_id, idx)
);
create index if not exists segments_media_start on segments (media_id, start_ms);

create table if not exists words (
  segment_id bigint not null references segments(id) on delete cascade,
  idx        int not null,
  start_ms   int not null,
  end_ms     int not null,
  text       text not null,
  primary key (segment_id, idx)
);

create table if not exists summaries (
  id            uuid primary key default gen_random_uuid(),
  media_id      uuid not null references media(id) on delete cascade,
  template_id   text not null default 'key_points',
  model         text not null,
  payload       jsonb not null,              -- ตรงกับ schema ของ template_id นั้น
  input_tokens  int,
  output_tokens int,
  cache_read_tokens int,
  cost_usd      numeric(10,4),
  created_at    timestamptz not null default now()
);
create unique index if not exists summaries_media_template
  on summaries (media_id, template_id);

-- idempotency: หนึ่งไฟล์ หนึ่งขั้น มีได้แถวเดียว retry แล้วไม่จ่ายค่าถอดเสียงซ้ำ
create table if not exists jobs (
  id         bigserial primary key,
  media_id   uuid not null references media(id) on delete cascade,
  step       text not null,                  -- normalize | asr | join | summarize
  attempt    int  not null default 0,
  state      text not null default 'queued', -- queued | running | done | failed
  error      text,
  updated_at timestamptz not null default now(),
  unique (media_id, step)
);
