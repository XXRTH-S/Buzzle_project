"""Opt-in tests against an isolated Docker database; providers are never called."""
import os
import io
import wave
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from app import db, storage
from app.main import app
from app.locking import media_lock, MediaBusy
from app.tasks import pipeline
from app.queue import cpu
from rq import SimpleWorker, Queue
from app.routers import media as media_routes


@unittest.skipUnless(os.getenv("BUZZLE_INTEGRATION_TESTS") == "1", "requires isolated DB")
class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        data = self.client.post("/api/media", json={"filename": "integration.wav", "summary_template": "board_meeting"}).json()
        self.mid, self.key = data["media_id"], data["storage_key"]

    def tearDown(self):
        self.client.delete(f"/api/media/{self.mid}")
        self.client.close()

    def test_lock_is_exclusive_and_released(self):
        with media_lock(self.mid):
            with self.assertRaises(MediaBusy):
                with media_lock(self.mid):
                    self.fail("second connection acquired lock")
        with media_lock(self.mid):
            pass

    def test_upload_range_and_active_overwrite(self):
        url = f"/api/upload/{self.key}"
        self.assertEqual(self.client.put(url, content=b"").status_code, 400)
        self.assertEqual(self.client.put(url, content=b"0123456789").status_code, 200)
        response = self.client.get(f"/api/media/{self.mid}/audio", headers={"Range": "bytes=2-5"})
        self.assertEqual(response.status_code, 206)
        self.assertEqual(response.content, b"2345")
        db.run("update media set status='done' where id=%s", (self.mid,))
        self.assertEqual(self.client.put(url, content=b"replace").status_code, 409)

    def test_join_preserves_words_and_empty_edit_invalidates_summary(self):
        pipeline._write_segments(self.mid, [{"start_ms": 120, "end_ms": 900, "text": "original", "words": [{"start_ms": 120, "end_ms": 900, "text": "original"}]}])
        segment = db.one("select * from segments where media_id=%s", (self.mid,))
        with patch.object(pipeline, "dispatch"):
            pipeline.join_step(self.mid)
        self.assertEqual(db.one("select count(*) n from words where segment_id=%s", (segment["id"],))["n"], 1)
        self.assertEqual(db.one("select id from segments where media_id=%s", (self.mid,))["id"], segment["id"])
        db.run("update media set status='done' where id=%s", (self.mid,))
        db.run("insert into summaries(media_id,model,payload) values(%s,'test','{}')", (self.mid,))
        response = self.client.patch(f"/api/segments/{segment['id']}", json={"text": ""})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["text"], "")
        self.assertEqual(self.client.get(f"/api/media/{self.mid}/summaries").json(), [])

    def test_missing_file_cannot_start_and_busy_delete_rejected(self):
        self.assertEqual(self.client.post(f"/api/media/{self.mid}/start").status_code, 409)
        with media_lock(self.mid):
            self.assertEqual(self.client.delete(f"/api/media/{self.mid}").status_code, 409)

    @patch.object(media_routes, "cpu")
    @patch.object(pipeline, "cpu")
    def test_real_queue_and_ffmpeg_with_stub_providers(self, pipeline_queue, api_queue):
        queue = Queue(f"integration-{self.mid}", connection=cpu().connection, default_timeout=3600)
        pipeline_queue.return_value = api_queue.return_value = queue
        self.assertEqual(queue.count, 0, "Use an idle isolated test queue")
        audio = io.BytesIO()
        with wave.open(audio, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(16000)
            wav.writeframes(b"\0\0" * 16000)
        self.assertEqual(self.client.put(f"/api/upload/{self.key}", content=audio.getvalue()).status_code, 200)
        with patch.object(pipeline.asr_registry, "get") as backend, patch.object(pipeline.summariser, "summarize") as summary:
            backend.return_value.transcribe.return_value = [{"start_ms": 0, "end_ms": 900, "text": "test"}]
            summary.return_value = ({"headline": "test", "summary": "test", "decisions": [], "action_items": [], "open_questions": []}, {"model": "openrouter:openrouter/free -> test", "input_tokens": 1, "output_tokens": 1, "cache_read_tokens": 0})
            self.assertEqual(self.client.post(f"/api/media/{self.mid}/start").status_code, 202)
            self.assertEqual(self.client.post(f"/api/media/{self.mid}/start").status_code, 202)
            self.assertEqual(queue.count, 1)
            SimpleWorker([queue], connection=queue.connection).work(burst=True, logging_level="WARNING")
            media = self.client.get(f"/api/media/{self.mid}").json()
            self.assertEqual(media["status"], "done", media)
            self.assertEqual(len(media["steps"]), 4)
            backend.return_value.transcribe.assert_called_once()
            summary.assert_called_once()
            self.assertEqual(summary.call_args.args[1], "board_meeting")
            self.assertEqual(media["summary_template"], "board_meeting")
            saved = self.client.get(f"/api/media/{self.mid}/summaries").json()
            self.assertEqual(saved[0]["template_id"], "board_meeting")
            self.assertEqual(self.client.get(f"/api/media/{self.mid}/audio").status_code, 200)

    def test_invalid_template_and_retry_preserves_choice(self):
        self.assertEqual(self.client.post("/api/media", json={"filename":"bad.wav", "summary_template":"unknown"}).status_code, 400)
        pipeline._write_segments(self.mid, [{"start_ms":0,"end_ms":900,"text":"test"}])
        with patch.object(pipeline, "dispatch") as dispatch:
            pipeline.join_step(self.mid)
            self.assertEqual(dispatch.call_args.args[-1], "board_meeting")
            dispatch.reset_mock()
            pipeline.join_step(self.mid)
            self.assertEqual(dispatch.call_args.args[-1], "board_meeting")


if __name__ == "__main__":
    unittest.main()
