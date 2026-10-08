"""SSE uses a synchronous iterator so Redis/DB waits run outside the event loop."""
import json
from uuid import UUID

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from .. import db, events

router = APIRouter(prefix="/api", tags=["events"])


@router.get("/media/{media_id}/events")
def stream(media_id: UUID):
    mid = str(media_id)
    if db.one("select id from media where id = %s", (mid,)) is None:
        raise HTTPException(404, "ไม่พบไฟล์นี้")

    def gen():
        pubsub = events.subscribe(mid)
        try:
            while True:
                snapshot = db.one("select status from media where id = %s", (mid,))
                if snapshot is None:
                    return
                yield _sse({"step": "snapshot", "state": snapshot["status"]})
                if snapshot["status"] in ("done", "failed"):
                    return
                message = pubsub.get_message(timeout=1.0)
                if message and isinstance(message.get("data"), str):
                    yield f"data: {message['data']}\n\n"
                else:
                    yield ": keep-alive\n\n"
        finally:
            pubsub.close()

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
