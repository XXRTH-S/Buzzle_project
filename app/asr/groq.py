"""Bounded demo ASR. No automatic retries or paid-provider fallbacks."""
import math
import wave
from pathlib import Path

import httpx

from ..config import settings
from .base import Segment


class GroqBackend:
    name = "groq"

    def transcribe(self, wav: Path, language: str = "auto") -> list[Segment]:
        s = settings()
        if not s.groq_api_key.strip():
            raise RuntimeError("GROQ_API_KEY is missing")
        if wav.stat().st_size > 20_000_000:
            raise ValueError("Groq demo accepts at most 20 MB")
        with wave.open(str(wav), "rb") as audio:
            duration = audio.getnframes() / audio.getframerate()
        if not 0 < duration <= 300:
            raise ValueError("Groq demo accepts audio up to 5 minutes")
        data = {"model": s.groq_asr_model, "response_format": "verbose_json",
                "timestamp_granularities[]": "segment", "temperature": "0"}
        if language != "auto":
            data["language"] = language
        try:
            with wav.open("rb") as audio:
                response = httpx.post(
                    "https://api.groq.com/openai/v1/audio/transcriptions",
                    headers={"Authorization": f"Bearer {s.groq_api_key}"},
                    data=data, files={"file": ("audio.wav", audio, "audio/wav")},
                    timeout=httpx.Timeout(120, connect=15),
                )
        except httpx.RequestError:
            raise RuntimeError("Groq connection failed; request was not retried") from None
        if response.status_code != 200:
            raise RuntimeError(f"Groq HTTP {response.status_code}; request was not retried")
        try:
            return self.parse(response.json(), duration)
        except (ValueError, TypeError, KeyError, AttributeError, OverflowError):
            raise RuntimeError("Groq returned invalid transcript or timestamps") from None

    @staticmethod
    def parse(payload: dict, duration: float) -> list[Segment]:
        rows = payload.get("segments")
        if not isinstance(rows, list):
            raise ValueError("Missing segments")
        result = []
        for row in rows:
            start, end = float(row["start"]), float(row["end"])
            text = row["text"]
            if not all(map(math.isfinite, (start, end))) or not 0 <= start <= end <= duration + 1:
                raise ValueError("Invalid time")
            if not isinstance(text, str):
                raise ValueError("Invalid text")
            if text.strip():
                result.append({"start_ms": round(start * 1000), "end_ms": round(end * 1000),
                               "text": text.strip(), "speaker": None, "confidence": None,
                               "words": []})
        if not result and payload.get("text", "").strip():
            raise ValueError("Text without timestamps")
        return result
