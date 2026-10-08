"""รูปแบบผลลัพธ์ของแต่ละเทมเพลต — ใช้เป็น output_format ของ messages.parse()"""
from typing import Literal

from pydantic import BaseModel, Field


class ActionItem(BaseModel):
    task: str
    owner: str                       # "ไม่ระบุ" ถ้าไม่ชัด ห้ามเดา
    due: str | None = None
    cite_ms: int                     # เวลาเริ่มของประโยคที่เป็นที่มา


class KeyPoints(BaseModel):
    """แบบ A — สาระสำคัญ"""
    headline: str
    summary: str
    decisions: list[str] = Field(default_factory=list)
    action_items: list[ActionItem] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)


class TimelineEntry(BaseModel):
    at_ms: int
    kind: Literal["topic", "decision", "assignment", "blocker", "schedule"]
    title: str
    detail: str
    speaker: str | None = None


class Timeline(BaseModel):
    """แบบ B — ไทม์ไลน์การทำ"""
    headline: str
    entries: list[TimelineEntry] = Field(min_length=1)
