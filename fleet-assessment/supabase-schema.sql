-- Run this in your Supabase SQL Editor
-- https://supabase.com → Project → SQL Editor → New Query

create table if not exists assessments (
  id                  uuid primary key default gen_random_uuid(),
  company_name        text,
  industry            text,
  state               text,
  total_fleet         integer,
  vehicles            jsonb,
  has_ev              boolean,
  miles_day           numeric,
  op_days             integer,
  hours_parked        numeric,
  monthly_fuel        numeric,
  kw_rate             numeric,
  ice_maint           numeric,
  insurance           numeric,
  ev_efficiency       numeric,
  ev_maint            numeric,
  ev_vehicle_cost     numeric,
  ev_next_12          integer,
  ev_next_36          integer,
  install_cost_us     numeric,
  install_price_client numeric,
  maint_fee_client    numeric,
  hw_cost             numeric,
  your_kwh_rate       numeric,
  results             jsonb,
  created_at          timestamptz default now()
);

-- Enable Row Level Security (optional but recommended)
alter table assessments enable row level security;

-- Allow all operations for now (tighten later with auth)
create policy "Allow all" on assessments for all using (true);
