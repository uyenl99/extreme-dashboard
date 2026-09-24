-- Run once in the existing Supabase project. No public access policies.
create table if not exists public.flat_monitor_relay (
  id integer primary key check (id=1),
  snapshot jsonb not null default '{}'::jsonb,
  updated_at timestamptz,
  command jsonb,
  command_id uuid,
  requested_at timestamptz,
  ack_id uuid
);
alter table public.flat_monitor_relay enable row level security;
revoke all on public.flat_monitor_relay from anon, authenticated;
grant select, update on public.flat_monitor_relay to service_role;
insert into public.flat_monitor_relay(id) values(1) on conflict do nothing;

-- Read-only verification of requested owner: expect exactly one confirmed user.
select id,email,email_confirmed_at from auth.users where lower(email)='uyenl99@yahoo.com';
