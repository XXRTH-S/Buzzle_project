"""ElevenLabs Scribe v2 — ทางหลักของโปรเจกต์

diarization มาในตัว ขั้นแยกผู้พูดจึงหายไปทั้งขั้น (ดู docs/architecture.md)
"""
from pathlib import Path

import httpx

from ..config import settings
from .base import Segment, Word, normalize_speaker

ENDPOINT = "https://api.elevenlabs.io/v1/speech-to-text"


class ScribeBackend:
    name = "scribe"

    def transcribe(self, wav: Path, language: str = "auto") -> list[Segment]:
        key = settings().elevenlabs_api_key
        if not key:
            raise RuntimeError("ยังไม่ได้ตั้ง ELEVENLABS_API_KEY ใน .env")

        data = {"model_id": "scribe_v1", "diarize": "true",
                "timestamps_granularity": "word"}
        if language != "auto":
            data["language_code"] = language

        with wav.open("rb") as fh:
            resp = httpx.post(
                ENDPOINT,
                headers={"xi-api-key": key},
                data=data,
                files={"file": (wav.name, fh, "audio/wav")},
                timeout=httpx.Timeout(600.0, connect=30.0),
            )
        resp.raise_for_status()
        return self._to_segments(resp.json())

    @staticmethod
    def _to_segments(payload: dict) -> list[Segment]:
        """รวมคำเป็นประโยคโดยตัดเมื่อผู้พูดเปลี่ยน หรือเงียบเกิน 800 ms"""
        seen: dict[str, str] = {}
        segments: list[Segment] = []
        current: Segment | None = None

        for w in payload.get("words", []):
            if w.get("type") not in (None, "word"):
                continue
            start = int(float(w.get("start", 0)) * 1000)
            end = int(float(w.get("end", 0)) * 1000)
            speaker = normalize_speaker(w.get("speaker_id"), seen)
            word: Word = {"start_ms": start, "end_ms": end, "text": w.get("text", "")}

            gap_too_long = current is not None and start - current["end_ms"] > 800
            speaker_changed = current is not None and current.get("speaker") != speaker

            if current is None or gap_too_long or speaker_changed:
                current = {"start_ms": start, "end_ms": end, "text": "",
                           "speaker": speaker, "confidence": None, "words": []}
                segments.append(current)

            current["words"].append(word)
            current["text"] += word["text"]
            current["end_ms"] = end

        if not segments and payload.get("text"):
            segments = [{"start_ms": 0, "end_ms": 0, "text": payload["text"],
                         "speaker": None, "confidence": None, "words": []}]
        return segments
