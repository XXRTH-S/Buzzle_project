"""faster-whisper บนเครื่อง — ใช้เป็น "ตัวเทียบคุณภาพ" เท่านั้น ไม่ใช่ทางหลัก

ข้อจำกัดของเครื่องพัฒนา (ดู docs/hardware.md):
  VRAM 6 GB เหลือใช้จริง ~4.2 GB → large-v3 int8_float16 (~4.7 GB) ไม่ผ่าน
  ให้ใช้ medium int8 (~1.5 GB) และรันบนคลิป 5-10 นาที
"""
from pathlib import Path

from ..config import settings
from .base import Segment, Word

_model = None


def _load():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel  # ติดตั้งเฉพาะใน Dockerfile.gpu

        s = settings()
        _model = WhisperModel(
            s.local_asr_model,
            device=s.local_asr_device,
            compute_type=s.local_asr_compute,
        )
    return _model


def release() -> None:
    """ปล่อย VRAM ก่อนสลับไปขั้นอื่น — บน 4.2 GB รันสองโมเดลพร้อมกันไม่ได้"""
    global _model
    _model = None
    try:
        import torch

        torch.cuda.empty_cache()
    except Exception:
        pass


class LocalWhisperBackend:
    name = "faster_whisper"

    def transcribe(self, wav: Path, language: str = "auto") -> list[Segment]:
        model = _load()
        raw, _info = model.transcribe(
            str(wav),
            language=None if language == "auto" else language,
            word_timestamps=True,
            vad_filter=True,
            # ปิดไว้เพื่อลดอาการหลอนเป็นประโยคซ้ำ ๆ ตอนเจอช่วงเงียบ
            condition_on_previous_text=False,
        )

        segments: list[Segment] = []
        for seg in raw:
            words: list[Word] = [
                {"start_ms": int(w.start * 1000),
                 "end_ms": int(w.end * 1000),
                 "text": w.word}
                for w in (seg.words or [])
            ]
            segments.append({
                "start_ms": int(seg.start * 1000),
                "end_ms": int(seg.end * 1000),
                "text": seg.text.strip(),
                "speaker": None,       # ทางนี้ต้องรัน pyannote แยก ทีละตัว
                "confidence": getattr(seg, "avg_logprob", None),
                "words": words or None,
            })
        return segments
