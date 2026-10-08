import tempfile
import unittest
import wave
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import httpx
from app.asr.groq import GroqBackend


class GroqTests(unittest.TestCase):
    def test_timestamps(self):
        result = GroqBackend.parse({"segments": [{"start": .1, "end": .8, "text": " hello "}]}, 1)
        self.assertEqual(result[0]["start_ms"], 100)
        self.assertEqual(result[0]["text"], "hello")
        self.assertIsNone(result[0]["speaker"])

    def test_invalid_timestamps(self):
        for start, end in ((-1, 1), (2, 1), (0, float("nan")), (0, 99)):
            with self.assertRaises(ValueError):
                GroqBackend.parse({"segments": [{"start": start, "end": end, "text": "x"}]}, 1)

    def test_no_fabricated_timestamps(self):
        with self.assertRaises(ValueError):
            GroqBackend.parse({"text": "hello", "segments": []}, 1)

    @patch("app.asr.groq.settings")
    @patch("app.asr.groq.httpx.post")
    def test_request_and_safe_errors(self, post, config):
        config.return_value = SimpleNamespace(groq_api_key="test-secret", groq_asr_model="whisper-large-v3-turbo")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.wav"
            with wave.open(str(path), "wb") as audio:
                audio.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
                audio.writeframes(b"\0\0" * 16000)
            post.return_value = httpx.Response(200, json={"segments": [{"start": 0, "end": 1, "text": "test"}]})
            self.assertEqual(GroqBackend().transcribe(path, "th")[0]["text"], "test")
            self.assertEqual(post.call_args.kwargs["data"]["language"], "th")
            for code in (401, 429, 500):
                post.reset_mock()
                post.return_value = httpx.Response(code, text="test-secret")
                with self.assertRaises(RuntimeError) as error:
                    GroqBackend().transcribe(path)
                self.assertNotIn("test-secret", str(error.exception))
                post.assert_called_once()


if __name__ == "__main__":
    unittest.main()
