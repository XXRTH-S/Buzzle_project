# Summary templates and PDF — 2026-10-08

## What changed

- Kept the existing yellow Buzzle design; added the selected template name,
  summary-only retry, and PDF download controls. A failed summary with an
  existing transcript no longer offers the generic restart button.
- Tightened summary instructions: distinguish proposals from approved decisions,
  preserve important conditions/numbers, avoid invented assignments, and return
  empty lists for unsupported sections. This is prompt tuning, not model training.
- Kept strict template-schema validation and rejection of incomplete responses.
  Provider finish reasons are now allowlisted in errors; raw provider output is
  never displayed. No automatic retry or paid fallback was added.
- Preview now respects `SUMMARY_MODEL` from `.env`; it still defaults to
  `openrouter/free`. Changing it requires recreating API and worker.
- Added `GET /api/media/{id}/summary.pdf?template={template_id}`. Exports the
  saved summary only, validates it, escapes text, blocks external resource fetches,
  and returns a no-store attachment. No extra LLM request occurs on download.
- PDF rendering uses WeasyPrint 68.0, Pango and packaged Thai fonts inside Docker.
  [Installation reference](https://doc.courtbouillon.org/weasyprint/v68.0/first_steps.html).

## Evidence and limitations

- Latest failing user job was stored with `key_points` and an incomplete-provider
  response error. This does not establish a template-routing bug. No original
  provider body/finish reason was retained, so its upstream cause is unknown.
- Two real free-provider calls using synthetic text succeeded: `board_meeting`
  and `training`. Free routing selected different models. This is a smoke test,
  not a guarantee of consistent quality, availability or quota.
- Backend suite: 36 discovered, 30 passed, 6 isolated-database integration tests
  skipped. New tests cover all seven template instructions/schemas, summary-only
  queue selection, PDF rendering, safe errors and missing/invalid export requests.
- `scripts/test_summary_pdf_web.py`: real browser with mocked media/provider
  responses; seven template selections and PDF download requests passed, PDF is
  disabled before a saved summary, no page errors or horizontal overflow at
  390px and 1280px. Mock downloads verify UI routing, not PDF byte validity.
- Separately, the real API exported an existing saved summary as HTTP 200,
  application/pdf with a valid PDF header. No transcript was sent externally.
- Eight synthetic PDF fixtures rendered successfully, including a seven-page
  document. Thai text extraction passed for all; visual samples of board meeting,
  timeline and a middle page of the long document were inspected.
- TypeScript check and production Docker build passed. Services were recreated;
  the old Redis database-0 queue still contains two untouched jobs.

## Before public deployment

This remains a localhost preview without authentication/ownership enforcement.
Do not expose the PDF route or existing media endpoints publicly yet.
`npm audit --omit=dev` found three dependency findings (Next.js critical,
sharp high, source-map-js high). Dependency upgrades require a separate tested
pass; no automatic audit fix was run.

- [Next.js advisory](https://github.com/advisories/GHSA-vcvr-r3jv-pc5j)
- [sharp advisory](https://github.com/advisories/GHSA-wq5f-xc86-pv6w)
- [source-map-js advisory](https://github.com/advisories/GHSA-68fv-2mgg-jv7q)

To use: open a media detail page, select a template, click the summary button,
wait for a saved result, then click Download PDF. For an existing failed summary,
use the template-specific retry button; old error text is not evidence that a
new request has already been sent.
