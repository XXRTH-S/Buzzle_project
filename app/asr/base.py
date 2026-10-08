"""สัญญาเดียวที่ทุก backend ต้องคืน — สลับ Scribe v2 กับโมเดล local ได้ด้วย env var เดียว

นี่คือจุดที่ทำให้ย้ายไป GPU ใหญ่กว่า (เช่น L4 24 GB) ได้ภายหลังโดยไม่แก้โค้ดชั้นบน
"""
from pathlib import Path
from typing import Protocol, TypedDict


class Word(TypedDict):
    start_ms: int
    end_ms: int
    text: str


class Segment(TypedDict, total=False):
    start_ms: int
    end_ms: int
    text: str
    speaker: str | None      # SPK_00 ... (None ถ้า backend ไม่คืนผู้พูด)
    confidence: float | None
    words: list[Word] | None


class ASRBackend(Protocol):
    name: str

    def transcribe(self, wav: Path, language: str = "auto") -> list[Segment]:
        ...


def normalize_speaker(raw: str | int | None, seen: dict[str, str]) -> str | None:
    """แปลงชื่อผู้พูดของ vendor ให้เป็น SPK_00, SPK_01 ... ตามลำดับที่เจอ"""
    if raw is None:
        return None
    key = str(raw)
    if key not in seen:
        seen[key] = f"SPK_{len(seen):02d}"
    return seen[key]
