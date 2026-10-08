"""ตัดคำและแบ่งประโยคภาษาไทย

ภาษาไทยไม่เว้นวรรคระหว่างคำ transcript ดิบจึงอ่านไม่ออก และการวัด WER ด้วย
split(" ") ให้ตัวเลขที่ไม่มีความหมาย (ดู docs/pitfalls.md ข้อ 2)

pythainlp ไม่ได้อยู่ในอิมเมจหลักเพราะโหลด corpus เพิ่ม — import แบบ lazy
แล้ว fallback เป็น regex ถ้าไม่มี
"""
import re

_MAX_CHARS = 180
_BREAK = re.compile(r"(?<=[.!?۔]|[ๆฯ])\s+|\n+")


def tokenize(text: str) -> list[str]:
    """ตัดคำ — ใช้กับการวัด WER เท่านั้น อย่าใช้ split(' ') กับภาษาไทย"""
    try:
        from pythainlp.tokenize import word_tokenize

        return word_tokenize(text, engine="newmm", keep_whitespace=False)
    except ImportError:
        return [t for t in re.split(r"\s+", text) if t]


def split_sentences(text: str) -> list[str]:
    """แบ่งประโยคเพื่อให้ transcript อ่านออกบนหน้าเว็บ"""
    try:
        from pythainlp.tokenize import sent_tokenize

        parts = [p.strip() for p in sent_tokenize(text, engine="crfcut") if p.strip()]
        if parts:
            return parts
    except (ImportError, Exception):
        pass

    parts = [p.strip() for p in _BREAK.split(text) if p and p.strip()]
    if not parts:
        parts = [text.strip()]
    return [chunk for p in parts for chunk in _hard_wrap(p)]


def _hard_wrap(text: str) -> list[str]:
    """กันประโยคยาวเกินจนอ่านไม่ไหว เมื่อไม่มีตัวแบ่งประโยคเลย"""
    if len(text) <= _MAX_CHARS:
        return [text]
    return [text[i:i + _MAX_CHARS] for i in range(0, len(text), _MAX_CHARS)]
