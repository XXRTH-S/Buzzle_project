"""Synthetic PDF QA fixtures; no database or provider calls."""
from pathlib import Path
from app.summaries.pdf import render_pdf
from app.summaries.templates import REGISTRY
from app.tests.test_summary_export import example

if __name__ == "__main__":
    out = Path("/tmp/buzzle-pdf-qa")
    out.mkdir(exist_ok=True)
    for id, template in REGISTRY.items():
        (out / f"{id}.pdf").write_bytes(render_pdf("ข้อมูลสมมติสำหรับทดสอบ.wav", id, example(template)))
    template = REGISTRY["training"]
    data = example(template)
    data = {**data, "sections": {key: [f"ข้อ {i+1}: ฝึกตรวจสอบข้อความถอดเสียง เปรียบเทียบข้อเท็จจริงกับต้นฉบับ และบันทึกสิ่งที่ต้องติดตามอย่างชัดเจน" for i in range(18)] for key in data["sections"]}}
    (out / "multipage.pdf").write_bytes(render_pdf("ทดสอบเอกสารหลายหน้า.wav", "training", data))
    print("Generated eight synthetic PDF fixtures")
