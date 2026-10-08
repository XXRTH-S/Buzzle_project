"""งานใน worker — หนึ่งขั้นหนึ่งฟังก์ชัน

หลักการเดียวที่ห้ามละเมิด: ทุกขั้นเขียนผลลัพธ์ลง Postgres ก่อนไปขั้นถัดไป
เพื่อให้ retry ได้ทีละขั้นโดยไม่ต้องถอดเสียงใหม่ทั้งไฟล์
ข้อผิดพลาดที่แพงที่สุดคือจ่ายค่าถอดเสียงซ้ำเพราะ retry
"""
import json
from contextvars import ContextVar
from functools import wraps
from pathlib import Path

from .. import db, events, storage
from ..asr import registry as asr_registry
from ..audio import normalize, vad
from ..config import settings
from ..locking import MediaBusy, media_lock
from ..queue import cpu, gpu
from ..summaries import run as summariser
from ..summaries.templates import DEFAULT_ID

WORK_DIR = Path("/srv/media/work")
_pending_dispatch: ContextVar[list | None] = ContextVar("pending_dispatch", default=None)


def dispatch(queue, function, *args):
    pending = _pending_dispatch.get()
    if pending is None:
        return queue.enqueue(function, *args)
    pending.append((queue, function, args))


def serialized(function):
    """Lock a media stage, then dispatch only AFTER releasing its lock."""
    @wraps(function)
    def wrapped(media_id, *args, **kwargs):
        pending = []
        token = _pending_dispatch.set(pending)
        try:
            try:
                with media_lock(media_id):
                    if db.one("select id from media where id = %s", (media_id,)) is None:
                        return
                    function(media_id, *args, **kwargs)
            except MediaBusy:
                return
        finally:
            _pending_dispatch.reset(token)
        for queue, next_function, next_args in pending:
            try:
                queue.enqueue(next_function, *next_args)
            except Exception:
                _status(media_id, "failed", "ส่งงานเข้าคิวไม่สำเร็จ กดเริ่มอีกครั้งเพื่อดำเนินต่อจากผลที่บันทึกแล้ว")
                raise
    return wrapped


# ---------------------------------------------------------------- ตัวช่วยสถานะ

def _claim(media_id: str, step: str, force: bool = False) -> bool:
    """idempotency gate — ถ้าขั้นนี้ done แล้วให้ข้าม ไม่รันซ้ำ"""
    with db.conn() as c:
        row = c.execute(
            """insert into jobs (media_id, step, state, attempt)
               values (%s, %s, 'running', 1)
               on conflict (media_id, step) do update
                 set state = 'running', error = null,
                     attempt = jobs.attempt + 1,
                     updated_at = now()
               where jobs.state <> 'done' or %s
               returning state, attempt""",
            (media_id, step, force),
        ).fetchone()
    return row is not None


def _finish(media_id: str, step: str, state: str, error: str | None = None) -> None:
    db.run(
        """update jobs set state = %s, error = %s, updated_at = now()
           where media_id = %s and step = %s""",
        (state, error, media_id, step),
    )


def _status(media_id: str, status: str, error: str | None = None) -> None:
    db.run(
        "update media set status = %s, error = %s where id = %s",
        (status, error, media_id),
    )


def _fail(media_id: str, step: str, exc: Exception) -> None:
    message = f"{type(exc).__name__}: {exc}"[:2000]
    _finish(media_id, step, "failed", message)
    _status(media_id, "failed", message)
    events.publish(media_id, step, "failed", error=message)


# ---------------------------------------------------------------- 02 normalize

@serialized
def normalize_step(media_id: str) -> None:
    step = "normalize"
    if not _claim(media_id, step):
        media = db.one("select asr_backend from media where id = %s", (media_id,))
        queue = gpu() if asr_registry.queue_for(media["asr_backend"]) == "gpu" else cpu()
        return dispatch(queue, transcribe_step, media_id)

    try:
        media = db.one("select * from media where id = %s", (media_id,))
        _status(media_id, "normalizing")
        events.publish(media_id, step, "running", 0.0)

        raw = storage.fetch_to(media["storage_key"], WORK_DIR / media_id / "raw.bin")
        original_duration = normalize.probe_duration_ms(raw)
        if not original_duration or original_duration > settings().max_duration_seconds * 1000:
            raise ValueError(f"ไฟล์ต้องมีเสียงและความยาวไม่เกิน {settings().max_duration_seconds / 60:g} นาที")
        wav = normalize.to_wav16k(raw, WORK_DIR / media_id / "audio16k.wav")

        duration = normalize.probe_duration_ms(wav)
        spans = vad.speech_spans(wav)
        speech_ms = sum(b - a for a, b in spans)

        db.run("update media set duration_ms = %s where id = %s", (duration, media_id))
        _finish(media_id, step, "done")
        events.publish(
            media_id, step, "done", 1.0,
            duration_ms=duration, speech_ms=speech_ms,
        )
    except Exception as exc:
        _fail(media_id, step, exc)
        raise

    queue = gpu() if asr_registry.queue_for(media["asr_backend"]) == "gpu" else cpu()
    dispatch(queue, transcribe_step, media_id)


# ---------------------------------------------------------------- 03 asr

@serialized
def transcribe_step(media_id: str) -> None:
    step = "asr"
    if not _claim(media_id, step):
        return dispatch(cpu(), join_step, media_id)

    media = db.one("select * from media where id = %s", (media_id,))
    try:
        _status(media_id, "transcribing")
        events.publish(media_id, step, "running", 0.0)

        media = db.one("select * from media where id = %s", (media_id,))
        wav = WORK_DIR / media_id / "audio16k.wav"
        if not wav.exists():
            raw = storage.fetch_to(media["storage_key"], WORK_DIR / media_id / "raw.bin")
            wav = normalize.to_wav16k(raw, wav)

        backend = asr_registry.get(media["asr_backend"])
        segments = backend.transcribe(wav, media.get("language") or "auto")

        _write_segments(media_id, segments)
        _finish(media_id, step, "done")
        events.publish(media_id, step, "done", 1.0, segments=len(segments))
    except Exception as exc:
        _fail(media_id, step, exc)
        raise
    finally:
        if media["asr_backend"] == "faster_whisper":
            # ปล่อย VRAM ก่อนสลับขั้น — 4.2 GB รันสองโมเดลพร้อมกันไม่ได้
            from ..asr import local_whisper

            local_whisper.release()

    dispatch(cpu(), join_step, media_id)


def _write_segments(media_id: str, segments: list[dict]) -> None:
    with db.conn() as c:
        c.execute("delete from segments where media_id = %s", (media_id,))
        for idx, seg in enumerate(segments):
            row = c.execute(
                """insert into segments
                     (media_id, idx, start_ms, end_ms, speaker, text_model, confidence)
                   values (%s, %s, %s, %s, %s, %s, %s)
                   returning id""",
                (media_id, idx, seg["start_ms"], seg["end_ms"],
                 seg.get("speaker"), seg["text"].strip(), seg.get("confidence")),
            ).fetchone()
            for widx, word in enumerate(seg.get("words") or []):
                c.execute(
                    """insert into words (segment_id, idx, start_ms, end_ms, text)
                       values (%s, %s, %s, %s, %s)
                       on conflict do nothing""",
                    (row["id"], widx, word["start_ms"], word["end_ms"], word["text"]),
                )


# ---------------------------------------------------------------- 04 join

@serialized
def join_step(media_id: str) -> None:
    """Validate source timestamps without destroying ASR segments or words."""
    step = "join"
    media = db.one("select summary_template from media where id = %s", (media_id,))
    template_id = media["summary_template"]
    if not _claim(media_id, step):
        return dispatch(cpu(), summarize_step, media_id, template_id)

    try:
        _status(media_id, "joining")
        events.publish(media_id, step, "running", 0.0)
        # Preserve source segmentation, IDs and word timestamps. Sentence re-alignment
        # requires a real alignment algorithm; proportional character timing is false precision.
        rows = db.many(
            "select id, start_ms, end_ms from segments where media_id = %s order by idx",
            (media_id,),
        )
        if any(row["start_ms"] < 0 or row["end_ms"] < row["start_ms"] for row in rows):
            raise ValueError("ASR คืน timestamp ที่ไม่ถูกต้อง")
        _finish(media_id, step, "done")
        events.publish(media_id, step, "done", 1.0, segments=len(rows))
    except Exception as exc:
        _fail(media_id, step, exc)
        raise

    dispatch(cpu(), summarize_step, media_id, template_id)


# ---------------------------------------------------------------- 05 summarize

@serialized
def summarize_step(media_id: str, template_id: str = DEFAULT_ID,
                   force: bool = False) -> None:
    step = f"summarize:{template_id}"
    previous = db.one(
        "select model from summaries where media_id = %s and template_id = %s",
        (media_id, template_id),
    )
    if previous and not summariser.model_cache_matches(previous["model"]):
        force = True
    if not _claim(media_id, step, force=force):
        _status(media_id, "done")
        return

    try:
        _status(media_id, "summarizing")
        events.publish(media_id, step, "running", 0.0, template=template_id)

        rows = db.many(
            "select * from segments where media_id = %s order by idx", (media_id,))
        if not rows:
            raise RuntimeError("ยังไม่มี transcript สำหรับไฟล์นี้")

        transcript = summariser.format_transcript(rows)
        payload, usage = summariser.summarize(transcript, template_id)

        db.run(
            """insert into summaries
                 (media_id, template_id, model, payload,
                  input_tokens, output_tokens, cache_read_tokens)
               values (%s, %s, %s, %s, %s, %s, %s)
               on conflict (media_id, template_id) do update
                 set payload = excluded.payload,
                     model = excluded.model,
                     input_tokens = excluded.input_tokens,
                     output_tokens = excluded.output_tokens,
                     cache_read_tokens = excluded.cache_read_tokens,
                     created_at = now()""",
            (media_id, template_id, usage.get("model", settings().summary_model), json.dumps(payload),
             usage["input_tokens"], usage["output_tokens"], usage["cache_read_tokens"]),
        )

        _finish(media_id, step, "done")
        _status(media_id, "done")
        events.publish(media_id, step, "done", 1.0, template=template_id, usage=usage)
    except Exception as exc:
        _fail(media_id, step, exc)
        raise
