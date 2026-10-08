"""Render saved, validated summaries. No LLM request or external resource fetch."""
from html import escape

from .templates import REGISTRY


def stamp(ms: int) -> str:
    seconds = max(0, ms // 1000)
    return f"{seconds // 3600:02}:{seconds // 60 % 60:02}:{seconds % 60:02}"


def render_html(filename: str, template_id: str, payload: dict) -> str:
    template = REGISTRY[template_id]
    data = template.schema.model_validate(payload).model_dump()
    e = lambda value: escape(str(value), quote=True)

    def group(title, items):
        body = "<ul>" + "".join(f"<li>{e(item)}</li>" for item in items) + "</ul>" if items else "<p class='muted'>ไม่พบข้อมูลส่วนนี้ในข้อความถอดเสียง</p>"
        return f"<section><h2>{e(title)}</h2>{body}</section>"

    content = f"<h1>{e(data['headline'])}</h1>"
    if template_id == "timeline":
        for entry in data["entries"]:
            content += f"<section><h2>{stamp(entry['at_ms'])} · {e(entry['title'])}</h2><p>{e(entry['detail'])}</p>"
            if entry.get("speaker"):
                content += f"<p class='muted'>{e(entry['speaker'])}</p>"
            content += "</section>"
    else:
        content += f"<p>{e(data['summary'])}</p>"
        if "sections" in data:
            for title in template.sections:
                content += group(title, data["sections"][title])
        else:
            content += group("การตัดสินใจ", data["decisions"])
            content += group("งานที่ต้องทำ", [f"[{stamp(a['cite_ms'])}] {a['task']} — {a['owner']}" + (f" · {a['due']}" if a.get("due") else "") for a in data["action_items"]])
            content += group("ยังไม่ได้ข้อสรุป", data["open_questions"])
    return f"""<!doctype html><html lang="th"><meta charset="utf-8">
    <title>Buzzle summary</title><style>
    @page {{ size: A4; margin: 18mm 18mm 22mm;
      @bottom-left {{ content: 'Buzzle · สรุปด้วย AI โปรดตรวจสอบกับต้นฉบับ'; font-size: 9pt; color: #666; }}
      @bottom-right {{ content: counter(page) ' / ' counter(pages); font-size: 9pt; }} }}
    body {{ font-family: 'Garuda', sans-serif; font-size: 11pt; line-height: 1.65; color: #29251f; overflow-wrap: anywhere; }}
    header {{ border-bottom: 3pt solid #e9be48; padding-bottom: 12pt; margin-bottom: 18pt; }}
    .brand {{ font-size: 19pt; font-weight: bold; }}
    .muted {{ color: #666; font-size: 10pt; }}
    h1 {{ font-size: 19pt; line-height: 1.4; }} h2 {{ font-size: 13pt; color: #79570d; break-after: avoid; }}
    p, li {{ white-space: pre-wrap; orphans: 3; widows: 3; }} ul {{ padding-left: 20pt; }}
    </style><header><div class="brand">Buzzle.</div><div>{e(template.label)}</div>
    <div class="muted">ไฟล์: {e(filename)}</div></header>{content}</html>"""


def render_pdf(filename: str, template_id: str, payload: dict) -> bytes:
    from weasyprint import HTML

    def deny_fetch(url, *args, **kwargs):
        raise ValueError("External resources are disabled for summary PDF")

    return HTML(string=render_html(filename, template_id, payload), url_fetcher=deny_fetch).write_pdf()
