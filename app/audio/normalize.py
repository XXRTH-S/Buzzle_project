"""ท่อเสียงก่อนถึงโมเดล — ffmpeg เป็น mono 16 kHz + loudnorm

ไฟล์จาก iPhone เป็น .m4a ที่บางตัวมี metadata แปลก ๆ ให้ผ่าน ffmpeg เสมอ
อย่าส่งไฟล์ดิบเข้าโมเดล
"""
import json
import subprocess
from pathlib import Path


def probe_duration_ms(src: Path) -> int | None:
    out = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json",
         "-show_format", str(src)],
        capture_output=True, text=True, timeout=30,
    )
    if out.returncode != 0:
        return None
    try:
        return int(float(json.loads(out.stdout)["format"]["duration"]) * 1000)
    except (KeyError, ValueError, json.JSONDecodeError):
        return None


def to_wav16k(src: Path, dest: Path) -> Path:
    """mono 16 kHz + loudnorm — รูปแบบที่ทุก ASR backend รับตรงกัน"""
    dest.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["ffmpeg", "-nostdin", "-y", "-i", str(src), "-vn",
         "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
         "-ac", "1", "-ar", "16000",
         "-c:a", "pcm_s16le", str(dest)],
        capture_output=True, text=True, timeout=1800,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg ล้มเหลว: {result.stderr[-2000:]}")
    return dest
