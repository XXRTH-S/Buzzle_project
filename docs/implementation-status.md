# Implementation status — 2026-09-15

## Implemented

- 2026-09-21: Select a summary template before upload. The chosen `summary_template` is validated, persisted per recording, reused by automatic summary/retry, and selected on the detail page. Preview migration applied; other existing deployments require `app/migrations/001_summary_template.sql`.
- Template-first verification: Docker production build and 27 backend tests passed. Playwright CLI verified upload gating, mobile overflow, selected-template upload payload and detail selection using mocked upload endpoints. Real provider quality remains untested.

- Next.js home/history and media detail pages; Thai Swiss-style UI, responsive layout.
- Native streaming audio player, clickable timestamps, transcript edits and template switching.
- OpenRouter free-only adapter retained; no paid fallback or live provider calls during development.
- PostgreSQL session advisory lock per media; completed stages are skipped, next stage dispatch occurs after lock release.
- Join validates source timing without deleting source segments or word timestamps.
- Transcript edits invalidate summaries in the same transaction; edits and summary requests reject active work.
- Local upload streams to a unique temporary file, limits to 500 MiB, rejects empty uploads, and atomically publishes under a lock.
- Maximum duration check before normalization: 60 minutes. Local source and normalized playback endpoints; deletion includes work files.
- Independent compose.preview.yml project and Dockerfile.web; Docker production build passed and preview runs on port 3210 (3200 was occupied). Original Compose and other checkout are not replaced.

## Verification and limitations

- `cd web; npm ci; npm run build` passed, including TypeScript.
- Browser smoke script: `scripts/test_web.py` passed with mocked API: consent gate, desktop/mobile layout, Timeline request and transcript edit. This is not proof of full pipeline functionality or real audio playback. Screenshots are in ignored `artifacts/`.
- `scripts/test_web_live.py` passed against Docker web and real API: health/list HTTP 200, no browser runtime errors. Preview screenshot: `artifacts/docker-preview.png`.
- Docker backend suite passed: 24 tests, including 5 opt-in integration tests against isolated PostgreSQL/Redis. Verified exclusive advisory lock/release, upload and HTTP Range playback, edit invalidation, source word preservation, duplicate-start suppression, and Redis/RQ + FFmpeg pipeline completion with stub ASR/LLM.
- No actual ASR, LLM, 30–60 minute benchmark, worker-process crash/recovery, or GPU inference memory test completed. The queue integration test uses RQ SimpleWorker, not the separate production worker process.
- This is not exactly-once delivery: a crash between DB commit and Redis enqueue can leave a queued job stuck. Durable outbox/reconciler and explicit recovery UI remain TODO. Provider timeout after remote completion may incur duplicate cost on manual retry.
- No authentication, per-user authorization, retention scheduler, or legal compliance certification. Bind locally; use consented synthetic demo audio. A checkbox alone does not establish PDPA compliance.
- Cloud ASR remains Scribe by default. Local summary, cloud choice per job, chunked long-transcript summary, and local diarization remain planned.
- Browser polling runs every three seconds; SSE endpoint is available but not consumed by these pages yet.

## Reproduce Docker tests

Run from this checkout, keeping the original stack separate:

```powershell
docker compose -f compose.preview.yml up -d --build db redis api web
docker compose -f compose.preview.yml exec -e PYTHONDONTWRITEBYTECODE=1 -e BUZZLE_INTEGRATION_TESTS=1 api python -m unittest discover -s app/tests -v
```

Preview: http://localhost:3210 and API http://localhost:8210. This preview intentionally has blank cloud keys and starts without a worker; it is for UI/API diagnostics, not live transcription. Run integration tests only against this idle preview database/queue. Test media records and files are deleted afterward. Start the preview worker only when testing failure states. It also has blank keys.

The preview database, Redis, API, and web use `restart: unless-stopped`, so they return automatically after Docker Desktop restarts. The worker intentionally has no restart policy because cloud keys are blank and external processing must be started deliberately.

For a real cloud end-to-end demo, first set `OPENROUTER_API_KEY` and `ELEVENLABS_API_KEY` privately in `.env`, then configure the chosen isolated stack to read it. Do not commit keys or send real personal recordings without appropriate permission. OpenRouter free model availability/quota is not guaranteed.
