"""ตัดช่วงเงียบก่อนส่งเข้าโมเดล

ค่าเริ่มต้นใช้ ffmpeg silencedetect เพราะไม่ต้องลง torch (~2 GB) ในอิมเมจหลัก
ถ้าต้องการความแม่นขึ้นให้สลับไป silero-vad ในอิมเมจ GPU — อินเทอร์เฟซเดียวกัน

เหตุผลที่ต้องทำขั้นนี้: ช่วงเงียบ เสียงเพลง หรือเสียงแอร์ ทำให้ Whisper
ผลิตประโยคซ้ำ ๆ ที่ไม่มีใครพูด (ดู docs/pitfalls.md ข้อ 1)
"""
import re
import subprocess
from pathlib import Path

_START = re.compile(r"silence_start: ([\d.]+)")
_END = re.compile(r"silence_end: ([\d.]+)")


def speech_spans(wav: Path, min_silence_s: float = 1.0,
                 noise_db: int = -35) -> list[tuple[int, int]]:
    """คืนช่วงที่ "มีเสียงพูด" เป็น (start_ms, end_ms)"""
    total = _duration_s(wav)
    if total is None:
        return []

    result = subprocess.run(
        ["ffmpeg", "-i", str(wav),
         "-af", f"silencedetect=noise={noise_db}dB:d={min_silence_s}",
         "-f", "null", "-"],
        capture_output=True, text=True,
    )
    log = result.stderr
    starts = [float(m) for m in _START.findall(log)]
    ends = [float(m) for m in _END.findall(log)]

    spans: list[tuple[float, float]] = []
    cursor = 0.0
    for i, s in enumerate(starts):
        if s > cursor:
            spans.append((cursor, s))
        cursor = ends[i] if i < len(ends) else total
    if cursor < total:
        spans.append((cursor, total))

    return [(int(a * 1000), int(b * 1000)) for a, b in spans if b - a > 0.2]


def _duration_s(wav: Path) -> float | None:
    out = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(wav)],
        capture_output=True, text=True,
    )
    try:
        return float(out.stdout.strip())
    except ValueError:
        return None
