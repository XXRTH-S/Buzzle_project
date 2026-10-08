import json
import unittest
from unittest.mock import patch
from uuid import uuid4

import httpx
from fastapi.testclient import TestClient
from app.main import app
from app.config import Settings
from app.summaries import openrouter
from app.summaries.pdf import render_html, render_pdf
from app.summaries.templates import REGISTRY


def example(template):
    if template.example:
        return template.example
    if template.id == "timeline":
        return {"headline": "ตัวอย่างทดสอบ", "entries": [{"at_ms": 0, "kind": "topic", "title": "เริ่มประชุม", "detail": "ทดสอบภาษาไทย", "speaker": None}]}
    return {"headline": "ตัวอย่างทดสอบ", "summary": "ทดสอบภาษาไทย", "decisions": [], "action_items": [], "open_questions": []}


class SummaryExportTests(unittest.TestCase):
    def test_selected_template_is_enqueued_without_asr(self):
        from app.routers import summaries
        for template in REGISTRY:
            with self.subTest(template=template), patch.object(summaries, "media_lock"), patch.object(summaries.db, "run"), patch.object(summaries.db, "one", side_effect=[{"status": "failed"}, None, {"id": 1}]), patch.object(summaries, "cpu") as queue:
                result = summaries.summarize(uuid4(), summaries.SummarizeRequest(template=template))
                self.assertEqual(result["template_id"], template)
                self.assertEqual(queue.return_value.enqueue.call_args.args[2], template)
                self.assertEqual(queue.return_value.enqueue.call_args.args[0].__name__, "summarize_step")

    def test_all_templates_reach_provider_and_validate(self):
        config = Settings(_env_file=None, openrouter_api_key="test")
        for id, template in REGISTRY.items():
            with self.subTest(template=id), patch.object(openrouter, "settings", return_value=config), patch.object(openrouter.httpx, "post") as post:
                post.return_value = httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": {"content": json.dumps(example(template))}}]})
                payload, _ = openrouter.summarize("[0:00:00.000] SPK_??: ตัวอย่างทดสอบ", id)
                request = post.call_args.kwargs["json"]
                self.assertEqual(request["response_format"]["json_schema"]["name"], id)
                self.assertEqual(request["messages"][-1]["content"], template.instruction)
                self.assertEqual(payload, template.schema.model_validate(example(template)).model_dump())

    def test_export_all_templates_and_escape_html(self):
        for id, template in REGISTRY.items():
            with self.subTest(template=id):
                html = render_html('<img src="http://bad">', id, example(template))
                self.assertIn("&lt;img", html)
                self.assertNotIn('<img src=', html)
                self.assertIn(template.label, html)
                for section in template.sections:
                    self.assertIn(section, html)
                self.assertTrue(render_pdf("ทดสอบ.wav", id, example(template)).startswith(b"%PDF-"))

    def test_endpoint_selected_template_and_no_llm(self):
        with TestClient(app) as client, patch("app.routers.summaries.db.one") as read, patch("app.summaries.pdf.render_pdf", return_value=b"%PDF-test") as render, patch.object(openrouter.httpx, "post") as post:
            id = str(uuid4())
            read.return_value = {"filename": "test.wav", "payload": example(REGISTRY["board_meeting"])}
            response = client.get(f"/api/media/{id}/summary.pdf?template=board_meeting")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers["content-type"], "application/pdf")
            self.assertIn("board_meeting.pdf", response.headers["content-disposition"])
            self.assertEqual(read.call_args.args[1], (id, "board_meeting"))
            self.assertEqual(render.call_args.args[1], "board_meeting")
            post.assert_not_called()
            read.return_value = None
            self.assertEqual(client.get(f"/api/media/{id}/summary.pdf?template=timeline").status_code, 404)
            self.assertEqual(client.get(f"/api/media/{id}/summary.pdf?template=invalid").status_code, 400)

    def test_provider_incomplete_is_safe_and_not_retried(self):
        with patch.object(openrouter, "settings", return_value=Settings(_env_file=None, openrouter_api_key="test")), patch.object(openrouter.httpx, "post") as post:
            post.return_value = httpx.Response(200, json={"choices": [{"finish_reason": "SECRET", "message": {"content": "{}"}}]})
            with self.assertRaisesRegex(RuntimeError, "unknown") as error:
                openrouter.summarize("test", "board_meeting")
            self.assertNotIn("SECRET", str(error.exception))
            post.assert_called_once()
