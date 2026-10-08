from uuid import UUID

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from .. import db
from ..locking import MediaBusy, media_lock
from ..queue import cpu
from ..summaries.templates import DEFAULT_ID, REGISTRY, listing
from ..summaries.run import model_cache_matches
from ..tasks import pipeline

router = APIRouter(prefix="/api", tags=["summaries"])


class SummarizeRequest(BaseModel):
    template: str = DEFAULT_ID
    force: bool = False


@router.get("/templates")
def templates() -> list[dict]:
    """frontend สร้างปุ่มจากตรงนี้ — เพิ่มเทมเพลตใน Python แล้วปุ่มโผล่เอง"""
    return listing()


@router.post("/media/{media_id}/summarize")
def summarize(media_id: UUID, body: SummarizeRequest) -> dict:
    if body.template not in REGISTRY:
        raise HTTPException(
            400, f"ไม่รู้จักเทมเพลต {body.template!r} (มี: {', '.join(REGISTRY)})")

    mid = str(media_id)
    try:
        with media_lock(mid):
            media = db.one("select status from media where id = %s", (mid,))
            if media is None:
                raise HTTPException(404, "ไม่พบไฟล์นี้")
            if media["status"] not in ("done", "failed"):
                raise HTTPException(409, "งานกำลังประมวลผลหรือยังไม่มีข้อความ")
            existing = db.one(
                "select * from summaries where media_id = %s and template_id = %s",
                (mid, body.template),
            )
            if existing and not body.force and model_cache_matches(existing["model"]):
                return {"status": "ready", "cached": True, **_shape(existing)}
            if not db.one("select id from segments where media_id = %s limit 1", (mid,)):
                raise HTTPException(409, "ยังไม่มีข้อความสำหรับสรุป")
            force = body.force or (existing is not None and not model_cache_matches(existing["model"]))
            db.run("update media set status = 'summarizing', error = null where id = %s", (mid,))
    except MediaBusy:
        raise HTTPException(409, "งานกำลังประมวลผล กรุณารอก่อน") from None
    try:
        cpu().enqueue(pipeline.summarize_step, mid, body.template, force)
    except Exception:
        db.run("update media set status = 'failed', error = 'Queue unavailable' where id = %s", (mid,))
        raise HTTPException(503, "คิวไม่พร้อม กรุณาลองใหม่") from None
    return {"status": "queued", "cached": False, "template_id": body.template}


@router.get("/media/{media_id}/summary")
def get_summary(media_id: UUID, template: str = DEFAULT_ID) -> dict:
    row = db.one(
        "select * from summaries where media_id = %s and template_id = %s",
        (str(media_id), template),
    )
    if row is None:
        raise HTTPException(404, "ยังไม่เคยสร้างสรุปด้วยเทมเพลตนี้")
    return _shape(row)


@router.get("/media/{media_id}/summaries")
def list_summaries(media_id: UUID) -> list[dict]:
    rows = db.many(
        "select * from summaries where media_id = %s", (str(media_id),))
    return [_shape(r) for r in rows]


@router.get("/media/{media_id}/summary.pdf")
def download_summary(media_id: UUID, template: str = DEFAULT_ID) -> Response:
    if template not in REGISTRY:
        raise HTTPException(400, "ไม่รู้จักเทมเพลต")
    row = db.one(
        "select s.payload, m.filename from summaries s join media m on m.id=s.media_id "
        "where s.media_id=%s and s.template_id=%s", (str(media_id), template),
    )
    if row is None:
        raise HTTPException(404, "ยังไม่มีสรุปสำหรับเทมเพลตนี้ กรุณาสร้างสรุปก่อน")
    from ..summaries.pdf import render_pdf
    return Response(render_pdf(row["filename"], template, row["payload"]),
                    media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="buzzle-{media_id}-{template}.pdf"',
                             "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})


def _shape(row: dict) -> dict:
    return {
        "template_id": row["template_id"],
        "model": row["model"],
        "payload": row["payload"],
        "usage": {
            "input_tokens": row["input_tokens"],
            "output_tokens": row["output_tokens"],
            # ถ้าค่านี้เป็น 0 ตลอด แปลว่า cache ไม่ติด — ไล่หาว่าอะไรทำให้ prefix เปลี่ยน
            "cache_read_tokens": row["cache_read_tokens"],
        },
        "created_at": row["created_at"],
    }
