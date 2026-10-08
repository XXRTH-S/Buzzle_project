-- Existing recordings retain the legacy summary choice. Safe to rerun.
alter table media add column if not exists summary_template text not null default 'key_points';
