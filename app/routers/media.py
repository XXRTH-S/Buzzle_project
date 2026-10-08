from uuid import UUID
from uuid import uuid4
import asyncio
import mimetypes
import shutil

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel

from .. import db, storage
from ..config import settings
from ..queue import cpu
from ..tasks import pipeline
from ..locking import MediaBusy, media_lock
from ..summaries.templates import DEFAULT_ID, REGISTRY

router = APIRouter(prefix="/api", tags=["media"])


class CreateMedia(BaseModel):
    filename: str
    language: str = "auto"
    summary_template: str = DEFAULT_ID


@router.post("/media")
def create_media(body: CreateMedia) -> dict:
    """ขอที่อัปโหลด — เบราว์เซอร์ส่งไฟล์ตรงเข้า object storage ไม่ผ่าน app server"""
    if body.summary_template not in REGISTRY:
        raise HTTPException(400, "ไม่รู้จักเทมเพลตสรุปที่เลือก")
    key = storage.new_key(body.filename)
    row = db.one(
        """insert into media (filename, storage_key, language, asr_backend, summary_template)
           values (%s, %s, %s, %s, %s)
           returning id""",
        (body.filename, key, body.language, settings().asr_backend, body.summary_template),
    )
    return {
        "media_id": str(row["id"]),
        "summary_template": body.summary_template,
        "storage_key": key,
        "upload": storage.upload_target(key),
    }


@router.put("/upload/{key:path}")
async def local_upload(key: str, request: Request) -> dict:
    """ทางรับไฟล์สำหรับ STORAGE_BACKEND=local เท่านั้น

    ของจริงใช้ presigned URL ของ S3/R2 แล้ว endpoint นี้จะไม่ถูกเรียก
    """
    if settings().storage_backend != "local":
        raise HTTPException(400, "ใช้ presigned URL ของ object storage แทน")
    media = await asyncio.to_thread(db.one, "select id, status from media where storage_key = %s", (key,))
    if media is None or media["status"] != "uploaded":
        raise HTTPException(409, "ไม่พบงานอัปโหลดหรือไฟล์เริ่มประมวลผลแล้ว")
    dest = storage.local_path(key)
    dest.parent.mkdir(parents=True, exist_ok=True)
    temp = dest.with_name(dest.name + "." + uuid4().hex + ".part")
    size = 0
    try:
        with temp.open("xb") as output:
            async for chunk in request.stream():
                size += len(chunk)
                if size > settings().max_upload_bytes:
                    raise HTTPException(413, "ไฟล์ใหญ่เกินขีดจำกัด 500 MiB")
                await asyncio.to_thread(output.write, chunk)
        if not size:
            raise HTTPException(400, "ไฟล์ว่าง")
        # Serialize publication against start/delete without locking the event loop.
        def publish_upload():
            with media_lock(str(media["id"])):
                current = db.one("select status from media where id = %s", (str(media["id"]),))
                if current is None or current["status"] != "uploaded":
                    raise HTTPException(409, "สถานะงานเปลี่ยนแล้ว กรุณาอัปโหลดใหม่")
                temp.replace(dest)
        await asyncio.to_thread(publish_upload)
    except MediaBusy:
        raise HTTPException(409, "งานนี้กำลังใช้งาน") from None
    finally:
        temp.unlink(missing_ok=True)
    return {"ok": True, "key": key}


@router.post("/media/{media_id}/start", status_code=202)
def start(media_id: UUID) -> dict:
    mid = str(media_id)
    try:
        with media_lock(mid):
            media = db.one("select * from media where id = %s", (mid,))
            if media is None:
                raise HTTPException(404, "ไม่พบไฟล์นี้")
            if media["status"] not in ("uploaded", "failed"):
                return {"media_id": mid, "status": media["status"]}
            if settings().storage_backend == "local" and not storage.local_path(media["storage_key"]).is_file():
                raise HTTPException(409, "ยังไม่ได้อัปโหลดไฟล์")
            db.run("update media set status = 'queued', error = null where id = %s", (mid,))
    except MediaBusy:
        return {"media_id": mid, "status": "running"}
    try:
        job = cpu().enqueue(pipeline.normalize_step, mid)
    except Exception:
        db.run("update media set status = 'failed', error = 'Queue unavailable' where id = %s", (mid,))
        raise HTTPException(503, "คิวไม่พร้อม กรุณาลองใหม่") from None
    return {"media_id": mid, "status": "queued", "job_id": job.id}


@router.get("/media")
def list_media(limit: int = 50) -> list[dict]:
    rows = db.many(
        """select id, filename, status, duration_ms, asr_backend, created_at
           from media order by created_at desc limit %s""",
        (limit,),
    )
    return [{**r, "id": str(r["id"])} for r in rows]


@router.get("/media/{media_id}")
def get_media(media_id: UUID) -> dict:
    media = db.one("select * from media where id = %s", (str(media_id),))
    if media is None:
        raise HTTPException(404, "ไม่พบไฟล์นี้")
    steps = db.many(
        "select step, state, attempt, error from jobs where media_id = %s",
        (str(media_id),),
    )
    return {**media, "id": str(media["id"]), "steps": steps}


@router.delete("/media/{media_id}")
def delete_media(media_id: UUID) -> dict:
    """ลบตามนโยบาย PDPA — ลบทั้งไฟล์ใน storage และทุกแถวที่อ้างถึง"""
    mid = str(media_id)
    try:
        with media_lock(mid):
            media = db.one("select * from media where id = %s", (mid,))
            if media is None:
                raise HTTPException(404, "ไม่พบไฟล์นี้")
            storage.delete_prefix(media["storage_key"])
            work = (pipeline.WORK_DIR / mid).resolve()
            if work.parent != pipeline.WORK_DIR.resolve():
                raise HTTPException(400, "Invalid work path")
            if work.exists():
                shutil.rmtree(work)
            db.run("delete from media where id = %s", (mid,))
    except MediaBusy:
        raise HTTPException(409, "งานกำลังประมวลผล รอให้ขั้นปัจจุบันจบก่อนลบ") from None
    return {"deleted": str(media_id)}


@router.get("/media/{media_id}/audio")
def audio(media_id: UUID):
    media = db.one("select * from media where id = %s", (str(media_id),))
    if media is None:
        raise HTTPException(404, "ไม่พบไฟล์นี้")
    wav = pipeline.WORK_DIR / str(media_id) / "audio16k.wav"
    if wav.is_file() and media["status"] not in ("uploaded", "queued", "normalizing"):
        return FileResponse(wav, media_type="audio/wav", content_disposition_type="inline")
    if settings().storage_backend == "local":
        raw = storage.local_path(media["storage_key"])
        if raw.is_file():
            return FileResponse(raw, media_type=mimetypes.guess_type(media["filename"])[0] or "application/octet-stream",
                                content_disposition_type="inline")
    raise HTTPException(404, "เสียงยังไม่พร้อมเล่น")
