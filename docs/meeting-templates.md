# Meeting summary templates

The home page starts with template selection at `/#templates`, followed by upload. No template is preselected: choose one and confirm upload consent to enable file selection. Five meeting templates have synthetic examples; key points and timeline remain selectable. The selection is frozen while uploading.

`POST /api/media` validates and persists `summary_template`. The worker reads it from PostgreSQL after transcription, including when resuming a completed join step, then invokes the selected LLM prompt/schema. The detail page initially selects the saved template. Other formats can still be generated later from the saved transcript without repeating ASR. Merely switching a template does not call the model.

Existing databases require `app/migrations/001_summary_template.sql` before deploying the API/worker. It adds one column without replacing existing rows; legacy recordings retain `key_points`. The isolated preview database has been migrated. For another deployment, pipe this SQL into that deployment's PostgreSQL `psql -v ON_ERROR_STOP=1` before restarting its API/worker. Fresh databases use the updated `app/schema.sql`.

| ID | Focus |
|---|---|
| general_meeting | Agenda, discussion, decisions, owners, follow-up |
| board_meeting | Strategy, proposals versus approved resolutions, budget, risk, governance |
| training | Learning objectives, skills, procedures, exercises, cautions, application |
| team_meeting | Progress, blockers, team agreements, next actions, dependencies |
| lecture | Thesis, concepts, reasoning, examples, takeaways, open questions |

The Python template registry is the source of labels, emphasis instructions, required sections, and examples. Each new template has its own Pydantic output schema. Missing information is represented by an empty list, and prompts prohibit invented names, deadlines, budgets, votes, or resolutions. These five formats do not provide clickable time citations; the existing Timeline format retains time-based navigation.

Tests use mocked provider responses to validate prompt/schema selection. They do not measure live model quality. Run `scripts/test_templates_web.py` against the isolated preview to check real catalogue previews and mocked media summary requests on mobile and desktop.
