-- Schéma pour MyFirstSandBox (à exécuter dans l'éditeur SQL de Supabase)
create table if not exists public.user_prefs (
  user_id uuid primary key references auth.users(id) on delete cascade,
  prefs jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);

alter table public.user_prefs enable row level security;

create policy "users read own prefs" on public.user_prefs
  for select using (auth.uid() = user_id);

create policy "users insert own prefs" on public.user_prefs
  for insert with check (auth.uid() = user_id);

create policy "users update own prefs" on public.user_prefs
  for update using (auth.uid() = user_id);
