from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import db
from .config import settings
from .routers import events, media, segments, summaries

app = FastAPI(
    title="Buzzle",
    description="ถอดเสียง + สรุปอัตโนมัติ พร้อมอ้างกลับไปยังวินาทีต้นทาง",
    version="0.1.0",
)

# Next.js รันบน host ไม่ได้อยู่ใน compose จึงเป็นคนละ origin
# ใช้พอร์ต 3100 เพราะ 3000 ถูกสแตกอื่นบนเครื่องนี้ใช้อยู่
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3100", "http://127.0.0.1:3100", "http://localhost:3200", "http://127.0.0.1:3200", "http://localhost:3210", "http://127.0.0.1:3210"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(media.router)
app.include_router(segments.router)
app.include_router(summaries.router)
app.include_router(events.router)


@app.get("/health")
def health() -> dict:
    checks: dict[str, str] = {}
    try:
        db.one("select 1 as ok")
        checks["db"] = "ok"
    except Exception:
        checks["db"] = "unavailable"

    s = settings()
    checks["asr_backend"] = s.asr_backend
    checks["summary_model"] = s.summary_model
    checks["summary_provider"] = s.summary_provider
    checks["summary_key"] = "set" if s.summary_key_present else "missing"
    checks["anthropic_key"] = "set" if s.anthropic_api_key else "missing"
    checks["asr_key"] = (
        "set" if (s.groq_api_key.strip() if s.asr_backend == "groq"
                  else s.elevenlabs_api_key.strip() if s.asr_backend == "scribe"
                  else s.asr_backend == "faster_whisper") else "missing"
    )
    ok = checks["db"] == "ok"
    return {"ok": ok, **checks}
