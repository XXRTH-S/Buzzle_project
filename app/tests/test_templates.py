import json
import unittest
from unittest.mock import patch
import httpx
from pydantic import ValidationError
from app.config import Settings
from app.summaries import openrouter
from app.summaries.templates import MEETING_TEMPLATES, listing


class MeetingTemplateTests(unittest.TestCase):
    def test_examples_match_each_schema_and_metadata(self):
        self.assertEqual(len(MEETING_TEMPLATES), 5)
        self.assertEqual(len(listing()), 7)
        for tpl in MEETING_TEMPLATES:
            with self.subTest(template=tpl.id):
                self.assertEqual(tpl.schema.model_validate(tpl.example).model_dump(), tpl.example)
                self.assertEqual(list(tpl.example["sections"]), list(tpl.sections))
                with self.assertRaises(ValidationError):
                    tpl.schema.model_validate({"headline": "wrong shape", "summary": "test"})
                with self.assertRaises(ValidationError):
                    tpl.schema.model_validate({"headline": "wrong sections", "summary": "test", "sections": {"wrong": []}})

    def test_provider_uses_selected_instructions_and_schema(self):
        config = Settings(_env_file=None, openrouter_api_key="test", summary_model="openrouter/free")
        for tpl in MEETING_TEMPLATES:
            with self.subTest(template=tpl.id), patch.object(openrouter, "settings", return_value=config), patch.object(openrouter.httpx, "post") as post:
                post.return_value = httpx.Response(200, json={"model":"mock:free", "choices":[{"finish_reason":"stop", "message":{"content":json.dumps(tpl.example)}}]})
                result, _ = openrouter.summarize("Transcript fixture", tpl.id)
                self.assertEqual(result, tpl.example)
                body = post.call_args.kwargs["json"]
                self.assertEqual(body["messages"][-1]["content"], tpl.instruction)
                schema = body["response_format"]["json_schema"]
                self.assertEqual(schema["name"], tpl.id)
                sections = schema["schema"]["$defs"][f"{tpl.id}_sections"]
                self.assertEqual(sections["required"], list(tpl.sections))
