import json
import unittest
from unittest.mock import patch

import httpx

from app.config import Settings
from app.summaries import openrouter, run
from app.summaries.schemas import KeyPoints


class OpenRouterTests(unittest.TestCase):
    def setUp(self):
        self.config = Settings(_env_file=None, summary_provider="openrouter",
                               summary_model="openrouter/free", openrouter_api_key="test-key")
        self.settings_patch = patch.object(openrouter, "settings", return_value=self.config)
        self.settings_patch.start()
        self.addCleanup(self.settings_patch.stop)
        self.payload = {"headline": "ประชุม", "summary": "ตกลงทดสอบระบบ",
                        "decisions": [], "action_items": [], "open_questions": []}

    def response(self, payload=None, **extra):
        return httpx.Response(200, json={
            "model": "example/model:free",
            "choices": [{"finish_reason": "stop", "message": {
                "content": json.dumps(self.payload if payload is None else payload)}}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 40,
                      "prompt_tokens_details": {"cached_tokens": 20}}, **extra})

    @patch.object(openrouter.httpx, "post")
    def test_key_points_request_and_usage(self, post):
        post.return_value = self.response()
        payload, usage = openrouter.summarize("[0:00:01.000] A: ทดสอบ", "key_points")
        self.assertEqual(payload, self.payload)
        request = post.call_args.kwargs
        self.assertEqual(request["headers"]["Authorization"], "Bearer test-key")
        self.assertEqual(request["json"]["model"], "openrouter/free")
        self.assertNotIn("models", request["json"])
        self.assertTrue(request["json"]["provider"]["require_parameters"])
        self.assertEqual(request["json"]["response_format"]["type"], "json_schema")
        self.assertEqual(usage["input_tokens"], 100)
        self.assertEqual(usage["cache_read_tokens"], 20)
        self.assertEqual(usage["model"], "openrouter:openrouter/free -> example/model:free")

    @patch.object(openrouter.httpx, "post")
    def test_timeline_and_specific_free_model(self, post):
        self.config.summary_model = "example/model:free"
        result = {"headline": "ทดสอบ", "entries": [{"at_ms": 1000, "kind": "topic",
                  "title": "หัวข้อ", "detail": "รายละเอียด", "speaker": None}]}
        post.return_value = self.response(result)
        self.assertEqual(openrouter.summarize("test", "timeline")[0], result)
        self.assertEqual(post.call_args.kwargs["json"]["response_format"]["json_schema"]["name"], "timeline")

    def test_strict_schema_nested_and_non_mutating(self):
        original = KeyPoints.model_json_schema()
        snapshot = json.dumps(original)
        strict = openrouter.strict_schema(original)
        self.assertEqual(json.dumps(original), snapshot)
        self.assertFalse(strict["additionalProperties"])
        action = strict["$defs"]["ActionItem"]
        self.assertFalse(action["additionalProperties"])
        self.assertIn("due", action["required"])
        self.assertNotIn("default", action["properties"]["due"])

    @patch.object(openrouter.httpx, "post")
    def test_paid_model_rejected_before_network(self, post):
        self.config.summary_model = "example/paid-model"
        with self.assertRaisesRegex(ValueError, "เฉพาะ"):
            openrouter.summarize("test", "key_points")
        post.assert_not_called()

    @patch.object(openrouter.httpx, "post")
    def test_missing_key_and_empty_transcript(self, post):
        self.config.openrouter_api_key = " "
        with self.assertRaisesRegex(RuntimeError, "OPENROUTER_API_KEY"):
            openrouter.summarize("test", "key_points")
        self.config.openrouter_api_key = "test"
        with self.assertRaises(ValueError):
            openrouter.summarize(" ", "key_points")
        post.assert_not_called()

    @patch.object(openrouter.httpx, "post")
    def test_errors_are_safe_and_do_not_retry(self, post):
        for status in (400, 401, 402, 403, 404, 413, 429, 500, 503):
            with self.subTest(status=status):
                post.reset_mock()
                post.return_value = httpx.Response(status, json={"error": "SECRET TRANSCRIPT"})
                with self.assertRaises(RuntimeError) as caught:
                    openrouter.summarize("test", "key_points")
                self.assertNotIn("SECRET", str(caught.exception))
                post.assert_called_once()

    @patch.object(openrouter.httpx, "post")
    def test_network_failures_sanitized(self, post):
        for error in (httpx.ReadTimeout("SECRET"), httpx.ConnectError("SECRET")):
            post.side_effect = error
            with self.assertRaises(RuntimeError) as caught:
                openrouter.summarize("test", "key_points")
            self.assertNotIn("SECRET", str(caught.exception))

    @patch.object(openrouter.httpx, "post")
    def test_bad_outputs_rejected(self, post):
        responses = [
            httpx.Response(200, text="not json"),
            httpx.Response(200, json={"choices": []}),
            self.response({"headline": "missing summary"}),
            self.response(choices=[{"finish_reason": "length", "message": {"content": "{}"}}]),
            self.response(choices=[{"finish_reason": "stop", "message": {"refusal": "SECRET"}}]),
            self.response(choices=[{"finish_reason": "stop", "message": {"content": None}}]),
            self.response(error={"code": 429, "message": "SECRET"}),
        ]
        for response in responses:
            with self.subTest(response=response):
                post.return_value = response
                with self.assertRaises(RuntimeError) as caught:
                    openrouter.summarize("test", "key_points")
                self.assertNotIn("SECRET", str(caught.exception))

    @patch.object(openrouter.httpx, "post")
    def test_usage_optional(self, post):
        post.return_value = self.response(usage=None, model=None)
        _, usage = openrouter.summarize("test", "key_points")
        self.assertIsNone(usage["input_tokens"])
        self.assertTrue(usage["model"].endswith(" -> unknown"))

    def test_provider_dispatch_and_cache_identity(self):
        with patch.object(run, "settings", return_value=self.config):
            with patch.object(openrouter, "summarize", return_value=({}, {})) as call:
                run.summarize("text", "timeline")
                call.assert_called_once_with("text", "timeline")
            self.assertFalse(run.model_cache_matches("claude-opus-5"))
            self.assertFalse(run.model_cache_matches("openrouter:other:free -> example/model"))
            self.assertTrue(run.model_cache_matches("openrouter:openrouter/free -> example/model"))
            self.config.summary_provider = "anthropic"
            self.config.summary_model = "test-anthropic"
            self.assertTrue(run.model_cache_matches("test-anthropic"))
            with patch.object(run, "_summarize_anthropic", return_value=({}, {})) as call:
                run.summarize("text", "key_points")
                call.assert_called_once()

    def test_health_key_selection(self):
        self.assertTrue(self.config.summary_key_present)
        self.config.summary_provider = "anthropic"
        self.config.anthropic_api_key = ""
        self.assertFalse(self.config.summary_key_present)

    def test_old_provider_cache_enqueues_regeneration(self):
        from uuid import uuid4
        from app.routers import summaries

        with patch.object(run, "settings", return_value=self.config), \
             patch.object(summaries, "media_lock"), \
             patch.object(summaries.db, "run"), \
             patch.object(summaries.db, "one", side_effect=[{"status": "done"}, {"model": "claude-opus-5"}, {"id": 1}]), \
             patch.object(summaries, "cpu") as queue:
            result = summaries.summarize(uuid4(), summaries.SummarizeRequest())
            self.assertEqual(result["status"], "queued")
            self.assertTrue(queue.return_value.enqueue.call_args.args[-1])

    def test_pipeline_records_actual_model_on_provider_change(self):
        from app.tasks import pipeline

        result_usage = {"input_tokens": 100, "output_tokens": 40, "cache_read_tokens": None,
                        "model": "openrouter:openrouter/free -> example/actual:free"}
        with patch.object(run, "settings", return_value=self.config), \
             patch.object(pipeline.db, "one", return_value={"model": "claude-opus-5"}), \
             patch.object(pipeline.db, "many", return_value=[{
                 "text_model": "ทดสอบ", "text_edited": None, "start_ms": 0, "speaker": None}]), \
             patch.object(pipeline.db, "run") as write, \
             patch.object(pipeline, "_claim", return_value=True), \
             patch.object(pipeline.events, "publish"), \
             patch.object(pipeline.summariser, "summarize", return_value=(self.payload, result_usage)):
            pipeline.summarize_step.__wrapped__("example-media")
            inserts = [c for c in write.call_args_list if "insert into summaries" in c.args[0]]
            self.assertEqual(len(inserts), 1)
            self.assertEqual(inserts[0].args[1][2], result_usage["model"])


if __name__ == "__main__":
    unittest.main()
