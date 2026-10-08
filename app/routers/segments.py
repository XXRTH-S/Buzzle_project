from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .. import db
from ..locking import MediaBusy, media_lock

router = APIRouter(prefix="/api", tags=["segments"])


class EditSegment(BaseModel):
    text: str


@router.get("/media/{media_id}/segments")
def list_segments(media_id: UUID, from_ms: int = 0) -> list[dict]:
    rows = db.many(
        """select id, idx, start_ms, end_ms, speaker, text_model, text_edited, confidence
           from segments
           where media_id = %s and end_ms >= %s
           order by idx""",
        (str(media_id), from_ms),
    )
    return [{**r, "text": r["text_edited"] if r["text_edited"] is not None else r["text_model"]} for r in rows]


@router.patch("/segments/{segment_id}")
def edit_segment(segment_id: int, body: EditSegment) -> dict:
    """เก็บฉบับที่คนแก้แยกจากฉบับโมเดล

    ส่วนต่างของสองคอลัมน์นี้คือ gold set ที่ได้มาฟรีจากผู้ใช้จริง ใช้วัด WER ใน M7
    """
    owner = db.one("select media_id from segments where id = %s", (segment_id,))
    if owner is None:
        raise HTTPException(404, "ไม่พบประโยคนี้")
    try:
        with media_lock(str(owner["media_id"])):
            media = db.one("select status from media where id = %s", (str(owner["media_id"]),))
            if media is None or media["status"] not in ("done", "failed"):
                raise HTTPException(409, "กรุณารอประมวลผลให้เสร็จก่อนแก้ไข")
            with db.conn() as c:
                row = c.execute(
                    """update segments set text_edited = %s where id = %s
                       returning id, idx, start_ms, end_ms, speaker, text_model, text_edited""",
                    (body.text, segment_id),
                ).fetchone()
                c.execute("delete from summaries where media_id = %s", (str(owner["media_id"]),))
                c.execute("delete from jobs where media_id = %s and step like 'summarize:%%'", (str(owner["media_id"]),))
    except MediaBusy:
        raise HTTPException(409, "งานกำลังประมวลผล กรุณาลองแก้ไขอีกครั้งภายหลัง") from None
    if row is None:
        raise HTTPException(404, "ไม่พบประโยคนี้")
    return {**row, "text": row["text_edited"]}


@router.get("/media/{media_id}/gold-diff")
def gold_diff(media_id: UUID) -> dict:
    """ประโยคที่คนแก้แล้ว — วัตถุดิบของ gold set ในโมดูล M7"""
    rows = db.many(
        """select idx, start_ms, text_model, text_edited
           from segments
           where media_id = %s and text_edited is not null
             and text_edited <> text_model
           order by idx""",
        (str(media_id),),
    )
    total = db.one(
        "select count(*) as n from segments where media_id = %s", (str(media_id),))
    return {"edited": len(rows), "total": total["n"], "rows": rows}
