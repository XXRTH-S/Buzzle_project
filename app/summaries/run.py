"""Summary dispatch: OpenRouter free by default, optional legacy Anthropic.

Provider prompt caching is an optimization, not a correctness requirement.
"""
from typing import Any

from ..config import settings
from .templates import BASE_SYSTEM, REGISTRY

_client: Any = None


def client() -> Any:
    global _client
    if _client is None:
        from anthropic import Anthropic

        _client = Anthropic(api_key=settings().anthropic_api_key or None)
    return _client


def format_transcript(segments: list[dict]) -> str:
    """ต้องมี ms ติดไปทุกบรรทัด ไม่งั้นโมเดลอ้าง cite_ms / at_ms ไม่ได้"""
    lines = []
    for s in segments:
        text = s["text_edited"] if s.get("text_edited") is not None else s["text_model"]
        lines.append(f"[{_stamp(s['start_ms'])}] {s.get('speaker') or 'SPK_??'}: {text}")
    return "\n".join(lines)


def _stamp(ms: int) -> str:
    total = ms // 1000
    return f"{total // 3600}:{total // 60 % 60:02d}:{total % 60:02d}.{ms % 1000:03d}"


def summarize(transcript: str, template_id: str) -> tuple[dict, dict]:
    """คืน (payload, usage) — payload ผ่าน schema ของเทมเพลตแล้ว"""
    if not transcript.strip():
        raise ValueError("ไม่มีข้อความสำหรับสรุป")
    if settings().summary_provider == "openrouter":
        from .openrouter import summarize as summarize_openrouter

        return summarize_openrouter(transcript, template_id)
    return _summarize_anthropic(transcript, template_id)


def model_cache_matches(stored_model: str) -> bool:
    s = settings()
    if s.summary_provider == "openrouter":
        return stored_model.startswith(f"openrouter:{s.summary_model} -> ")
    return stored_model == s.summary_model


def _summarize_anthropic(transcript: str, template_id: str) -> tuple[dict, dict]:
    if not settings().summary_key_present:
        raise RuntimeError("ยังไม่ได้ตั้ง ANTHROPIC_API_KEY ใน .env")
    tpl = REGISTRY[template_id]

    resp = client().messages.parse(
        model=settings().summary_model,
        max_tokens=16000,
        thinking={"type": "adaptive"},
        output_config={"effort": "high"},
        system=BASE_SYSTEM,
        messages=[{
            "role": "user",
            "content": [
                # ---- ไม่เปลี่ยนระหว่างเทมเพลต อยู่ก่อน breakpoint ----
                {"type": "text", "text": transcript,
                 "cache_control": {"type": "ephemeral"}},
                # ---- เปลี่ยนตามเทมเพลต อยู่หลัง breakpoint ----
                {"type": "text", "text": tpl.instruction},
            ],
        }],
        output_format=tpl.schema,
    )

    usage = {
        "input_tokens": getattr(resp.usage, "input_tokens", None),
        "output_tokens": getattr(resp.usage, "output_tokens", None),
        "cache_read_tokens": getattr(resp.usage, "cache_read_input_tokens", None),
    }
    return resp.parsed_output.model_dump(), usage
