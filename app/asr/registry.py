from ..config import settings
from .base import ASRBackend


def get(name: str | None = None) -> ASRBackend:
    name = name or settings().asr_backend
    if name == "groq":
        from .groq import GroqBackend

        return GroqBackend()
    if name == "scribe":
        from .scribe import ScribeBackend

        return ScribeBackend()
    if name == "faster_whisper":
        from .local_whisper import LocalWhisperBackend

        return LocalWhisperBackend()
    raise ValueError(f"ไม่รู้จัก ASR backend: {name!r} (ใช้ได้: scribe, faster_whisper, groq)")


def queue_for(name: str | None = None) -> str:
    """backend ที่รันเองต้องเข้าคิว gpu ซึ่งตั้ง concurrency = 1"""
    name = name or settings().asr_backend
    return "gpu" if name == "faster_whisper" else "cpu"
