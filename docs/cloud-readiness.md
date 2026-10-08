# Cloud readiness — 2026-10-08

## Implemented in this step

- Groq ASR adapter using the existing HTTP client; opt in with `ASR_BACKEND=groq`.
- Only normalized WAV up to 300 seconds and 20,000,000 bytes is accepted.
- Segment timestamps are validated; speaker labels are not fabricated.
- No automatic retries, provider fallback, or changes to account billing.
- `scripts/check_cloud_keys.py` performs read-only Groq model-list, OpenRouter key,
  and Supabase bucket checks, printing status only. It never uploads recordings.
- Inngest keys are not validated until its app integration is implemented.

## Database checkpoint — 2026-10-08

- Local `DATABASE_URL` now uses the project Session pooler (port 5432) with
  `sslmode=require`. The bootstrap verified that the connection actually uses TLS.
- `scripts/bootstrap_cloud_db.py` completed a validated dry run and rollback,
  then `--apply` completed with `Committed`.
- Created `media`, `segments`, `words`, `summaries`, and `jobs` from
  `app/schema.sql`; RLS is enabled on all five. No sample records were inserted.
- Revoked table/sequence privileges from PUBLIC, anon, and authenticated.
  An independent post-commit check confirmed both client roles have no table access.
- Security advisor: five informational `RLS Enabled No Policy` findings are
  intentional deny-all until the ownership/authentication design is implemented.
  [Advisor guidance](https://supabase.com/docs/guides/database/database-linter?lint=0008_rls_enabled_no_policy).
- Performance advisor: the new `segments_media_start` index is unused because
  the database has not served recordings yet; retain it for timestamp queries.
  [Advisor guidance](https://supabase.com/docs/guides/database/database-linter?lint=0005_unused_index).
- The bootstrap refuses to overwrite existing objects. Do not rerun it to update
  an initialized database; use reviewed incremental migrations. This bootstrap
  does not register Supabase CLI migration history.
- The backend still connects as a privileged database role. RLS does not protect
  users from unauthenticated backend endpoints using that role. Before public
  deployment, implement authentication/ownership checks and a least-privilege
  runtime role. TLS `require` encrypts transport; certificate identity verification
  is a separate hardening step.

## Still required before deployment

Read-only checks on 2026-10-07: Groq models and OpenRouter key endpoints returned
HTTP 200. Supabase bucket listing returned HTTP 200; the configured bucket was
corrected to the user-confirmed existing bucket and verified private. The first
Groq request without an app User-Agent returned 403; the follow-up returned 200.
This does not validate transcription quality, available quotas or paid/free billing.
Four mocked Groq unit tests passed; Docker integration was not run because the
Docker engine was unavailable. Existing ASR_BACKEND was not switched automatically.

- Baseline migration tracking and least-privilege runtime database credentials.
- Supabase storage adapter or complete S3 credentials, including signed playback.
- Bucket identity/private state is confirmed; storage integration still needs testing.
- Inngest integration, authenticated endpoints, per-user limits and retention.
- Render/Vercel configuration and HTTPS origins; no public deployment yet.
- Live transcription with an explicitly selected non-sensitive test recording.

## Local preview connected — 2026-10-08

- `compose.preview.yml` now forwards only Groq/OpenRouter keys from Compose's
  `.env` interpolation to API and worker. It does not forward cloud/admin secrets.
- Both services use Groq, the same local Preview Postgres/media volume, and Redis
  database 1. This deliberately does not switch the preview to Supabase.
- Redis database 1 was empty before startup. Two old jobs in database 0 remain
  untouched. Do not point the worker back at database 0 to recover old jobs.
- API health reports database OK and both required keys set. One worker is
  registered on database 1; its queue was empty after startup.
- Ten mocked Groq/pipeline tests passed inside the API container. No real audio
  has been sent; this is readiness verification, not an end-to-end ASR result.
- Demo limit is 300 seconds (5 minutes); the Groq adapter also caps normalized
  WAV at 20 MB. Any existing UI copy mentioning 60 minutes describes the previous
  local configuration, not the active Groq preview limit.
- New uploads use Groq; existing media retain their previously stored backend.
  Test with a new, non-sensitive recording rather than retrying old recordings.
- Recreate services after changing provider keys:
  `docker compose -f compose.preview.yml up -d --no-deps --force-recreate api worker`.
  Never print expanded `docker compose config` output: it contains interpolated keys.
