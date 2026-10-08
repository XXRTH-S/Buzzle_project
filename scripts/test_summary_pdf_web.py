"""UI contract test with synthetic media; never calls an LLM or writes the DB."""
import json
import re
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

OUT = Path(__file__).resolve().parents[1] / "artifacts" / "summary-export"
OUT.mkdir(parents=True, exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, channel="chrome")
    try:
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        errors, calls, downloads, saved = [], [], [], []
        page.on("pageerror", lambda error: errors.append(str(error)))
        templates = page.request.get("http://localhost:8210/api/templates").json()
        def example(t):
            if t.get("example"):
                return t["example"]
            if t["id"] == "timeline":
                return {"headline": "ข้อมูลสมมติสำหรับทดสอบ", "entries": [{"at_ms": 0, "kind": "topic", "title": "เริ่มทดสอบ", "detail": "ทดสอบภาษาไทย", "speaker": None}]}
            return {"headline": "ข้อมูลสมมติสำหรับทดสอบ", "summary": "ทดสอบภาษาไทย", "decisions": [], "action_items": [], "open_questions": []}
        def mock(route):
            headers = {"Access-Control-Allow-Origin": "http://localhost:3210", "Access-Control-Allow-Headers": "content-type", "Access-Control-Allow-Methods": "GET, POST, OPTIONS"}
            if route.request.method == "OPTIONS":
                route.fulfill(status=204, headers=headers)
                return
            path = route.request.url.split("/api/media/demo")[-1]
            if path == "":
                data = {"id": "demo", "filename": "ข้อมูลสมมติ.wav", "status": "failed", "summary_template": "key_points"}
            elif path == "/segments":
                data = [{"id": 1, "idx": 0, "start_ms": 0, "end_ms": 1000, "text": "ข้อมูลสมมติ", "text_model": "ข้อมูลสมมติ", "text_edited": None, "speaker": None}]
            elif path == "/summaries":
                data = saved
            elif path == "/summarize":
                body = route.request.post_data_json
                calls.append(body["template"])
                tpl = next(t for t in templates if t["id"] == body["template"])
                saved[:] = [s for s in saved if s["template_id"] != tpl["id"]]
                saved.append({"template_id": tpl["id"], "model": "mock", "payload": example(tpl), "usage": {"input_tokens": 1, "output_tokens": 1, "cache_read_tokens": 0}})
                data = {"status": "ready", "cached": False}
            elif path.startswith("/summary.pdf?"):
                downloads.append(path.split("template=")[-1])
                route.fulfill(status=200, headers=headers, content_type="application/pdf", body=b"%PDF-mocked-download")
                return
            elif path == "/audio":
                route.fulfill(status=404)
                return
            else:
                raise AssertionError(f"Unexpected media action: {path}")
            route.fulfill(status=200, headers=headers, content_type="application/json", body=json.dumps(data))
        page.route(re.compile(r"/api/media/demo(?:[/?].*)?$"), mock)
        page.goto("http://localhost:3210/media/demo")
        page.wait_for_load_state("networkidle")
        expect(page.get_by_role("heading", name="ข้อมูลสมมติ.wav", exact=True)).to_be_visible()
        print(page.get_by_role("button").all_text_contents())
        expect(page.get_by_role("button", name="ดาวน์โหลด PDF", exact=True)).to_be_disabled()
        for tpl in templates:
            page.get_by_role("tab", name=tpl["label"], exact=False).click()
            expect(page.get_by_role("heading", name="สรุปแบบ · " + tpl["label"], exact=True)).to_be_visible()
            page.get_by_role("button", name="ลองสรุปใหม่ตามแบบที่เลือก", exact=True).click()
            expect(page.get_by_role("button", name="สร้างสรุปใหม่", exact=True)).to_be_enabled()
            with page.expect_download() as download:
                page.get_by_role("button", name="ดาวน์โหลด PDF", exact=True).click()
            assert tpl["id"] in download.value.suggested_filename
        assert calls == downloads == [t["id"] for t in templates]
        for width in (1280, 390):
            page.set_viewport_size({"width": width, "height": 900})
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            page.screenshot(path=str(OUT / f"summary-{width}.png"), full_page=True)
        assert not errors, errors
        metadata = page.locator('.summary-metadata')
        expect(metadata).not_to_have_attribute('open', '')
        metadata.locator('summary').click()
        expect(metadata).to_have_attribute('open', '')
        home = page.get_by_role('link', name='Home · หน้าแรก', exact=True)
        expect(home).to_be_visible()
        home.click()
        page.wait_for_url('http://localhost:3210/')
        expect(page.get_by_role('link', name='Home · หน้าแรก', exact=True)).to_have_attribute('aria-current', 'page')
        print("PASS: seven selected template requests, seven downloads, disabled PDF before summary, mobile/desktop layout, no page errors")
        print("PASS: collapsible model details and Home navigation")
    finally:
        browser.close()
