"""เครื่องมือบรรทัดคำสั่งสำหรับเวิร์กช็อป

รันในคอนเทนเนอร์:
    docker compose exec api python -m app.cli health
    docker compose exec api python -m app.cli ingest /srv/media/in/meeting.m4a
    docker compose exec api python -m app.cli compare /srv/media/in/clip.wav
    docker compose exec api python -m app.cli summarize <media_id> timeline
"""
import argparse
import json
import sys
import time
from pathlib import Path

from . import db, storage
from .asr import registry as asr_registry
from .audio import normalize, vad
from .config import settings
from .summaries.templates import REGISTRY
from .tasks import pipeline


def cmd_health(_args) -> int:
    s = settings()
    try:
        db.one("select 1 as ok")
        print("db            : ok")
    except Exception as exc:
        print(f"db            : ล้มเหลว — {exc}")
        return 1
    print(f"asr_backend   : {s.asr_backend}")
    print(f"summary_model : {s.summary_model}")
    print(f"summary provider : {s.summary_provider}")
    print(f"summary key   : {'ตั้งแล้ว' if s.summary_key_present else 'ยังไม่ได้ตั้ง'}")
    print(f"asr key       : {'ตั้งแล้ว' if s.elevenlabs_api_key else 'ยังไม่ได้ตั้ง'}")
    return 0


def cmd_ingest(args) -> int:
    """ใส่ไฟล์จากดิสก์เข้าท่อ โดยไม่ต้องผ่านหน้าเว็บ"""
    src = Path(args.path)
    if not src.exists():
        print(f"ไม่พบไฟล์: {src}")
        return 1

    key = storage.new_key(src.name)
    storage.write(key, src.read_bytes())
    row = db.one(
        """insert into media (filename, storage_key, language, asr_backend)
           values (%s, %s, %s, %s) returning id""",
        (src.name, key, args.language, settings().asr_backend),
    )
    media_id = str(row["id"])
    print(f"media_id = {media_id}")

    if args.inline:
        pipeline.normalize_step(media_id)
    else:
        from .queue import cpu

        cpu().enqueue(pipeline.normalize_step, media_id)
        print("เข้าคิวแล้ว — ดู log ด้วย: docker compose logs -f worker")
    return 0


def cmd_compare(args) -> int:
    """โมดูล M2 — เทียบ backend บนไฟล์เดียวกัน

    ทางหลัก (scribe) รันบนไฟล์เต็มได้ ส่วนทางที่รันเองให้ใช้คลิป 5-10 นาที
    เพราะ VRAM เหลือ ~4.2 GB (ดู docs/hardware.md)
    """
    src = Path(args.path)
    wav = normalize.to_wav16k(src, Path("/tmp/compare16k.wav"))
    duration = normalize.probe_duration_ms(wav) or 0
    spans = vad.speech_spans(wav)
    speech = sum(b - a for a, b in spans)
    print(f"ไฟล์ {src.name} · ยาว {duration/1000:.1f} วิ · มีเสียงพูด {speech/1000:.1f} วิ\n")

    for name in args.backends:
        try:
            backend = asr_registry.get(name)
        except ValueError as exc:
            print(f"{name:16s} ข้าม — {exc}")
            continue
        started = time.time()
        try:
            segments = backend.transcribe(wav, args.language)
        except Exception as exc:
            print(f"{name:16s} ล้มเหลว — {type(exc).__name__}: {exc}")
            continue
        elapsed = time.time() - started
        rtf = elapsed / (duration / 1000) if duration else 0
        speakers = {s.get("speaker") for s in segments if s.get("speaker")}
        print(f"{name:16s} {elapsed:6.1f} วิ · RTF {rtf:.3f} · "
              f"{len(segments):4d} ประโยค · ผู้พูด {len(speakers) or '—'}")
        if args.show:
            for s in segments[:args.show]:
                print(f"    [{s['start_ms']:>8}] {s.get('speaker') or 'SPK_??'}: {s['text'][:70]}")
        print()
    return 0


def cmd_summarize(args) -> int:
    if args.template not in REGISTRY:
        print(f"ไม่รู้จักเทมเพลต {args.template!r} (มี: {', '.join(REGISTRY)})")
        return 1
    pipeline.summarize_step(args.media_id, args.template, force=args.force)
    row = db.one(
        "select * from summaries where media_id = %s and template_id = %s",
        (args.media_id, args.template),
    )
    if row is None:
        print("ไม่มีผลลัพธ์")
        return 1
    print(json.dumps(row["payload"], ensure_ascii=False, indent=2))
    print(f"\ntokens in={row['input_tokens']} out={row['output_tokens']} "
          f"cache_read={row['cache_read_tokens']}")
    if row["cache_read_tokens"] in (0, None):
        print("ไม่มีรายงาน cache hit สำหรับคำขอนี้ (ไม่ใช่ข้อผิดพลาด)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="app.cli")
    subs = parser.add_subparsers(dest="cmd", required=True)

    subs.add_parser("health").set_defaults(fn=cmd_health)

    p_in = subs.add_parser("ingest", help="ใส่ไฟล์เข้าท่อ")
    p_in.add_argument("path")
    p_in.add_argument("--language", default="auto")
    p_in.add_argument("--inline", action="store_true", help="รันตรงนี้ ไม่เข้าคิว")
    p_in.set_defaults(fn=cmd_ingest)

    p_cmp = subs.add_parser("compare", help="เทียบ ASR backend บนไฟล์เดียวกัน")
    p_cmp.add_argument("path")
    p_cmp.add_argument("--backends", nargs="+", default=["scribe"])
    p_cmp.add_argument("--language", default="auto")
    p_cmp.add_argument("--show", type=int, default=3, help="พิมพ์ตัวอย่างกี่ประโยค")
    p_cmp.set_defaults(fn=cmd_compare)

    p_sum = subs.add_parser("summarize", help="สรุปด้วยเทมเพลตที่เลือก")
    p_sum.add_argument("media_id")
    p_sum.add_argument("template", nargs="?", default="key_points")
    p_sum.add_argument("--force", action="store_true")
    p_sum.set_defaults(fn=cmd_summarize)

    args = parser.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
