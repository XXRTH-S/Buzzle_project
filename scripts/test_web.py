"""Browser smoke test with mocked API. Does not call ASR or LLM providers."""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts"
OUT.mkdir(exist_ok=True)
WEB = os.getenv("TEST_WEB_URL", "http://127.0.0.1:3200")
API = os.getenv("TEST_API_URL", "http://localhost:8100")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, channel="chrome")
    try:
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        errors = []
        segment = {"id": 1, "idx": 0, "start_ms": 1000, "end_ms": 5000, "speaker": None,
                   "text": "ข้อความทดสอบ", "text_model": "ข้อความทดสอบ", "text_edited": None}
        edited = []
        requests = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        def mock(route):
            path = route.request.url.removeprefix(API)
            data = {"summary_key": "missing", "asr_key": "missing"} if path == "/health" else []
            if path == "/api/templates":
                data = [{"id": "key_points", "label": "สาระสำคัญ", "hint": "สรุป"},
                        {"id": "timeline", "label": "ไทม์ไลน์การทำ", "hint": "ตามเวลา"}]
            elif path == "/api/media/demo":
                data = {"id": "demo", "filename": "fixture-demo.wav", "status": "done", "duration_ms": 5000, "created_at": "2026-09-15"}
            elif path == "/api/media/demo/segments":
                data = [segment]
            elif path == "/api/segments/1":
                text = route.request.post_data_json["text"]
                segment.update(text=text, text_edited=text)
                edited.append(text)
                data = segment
            elif path == "/api/media/demo/summarize":
                requests.append(route.request.post_data_json)
                data = {"status": "queued", "cached": False}
            route.fulfill(status=200, content_type="application/json", body=json.dumps(data))
        page.route(API + "/**", mock)
        page.goto(WEB)
        page.wait_for_load_state("networkidle")
        print(page.locator("body").inner_text())
        expect(page.locator('[data-brand-mark="voice-note-bee"]')).to_have_count(2)
        expect(page.get_by_role("link", name="Buzzle หน้าหลัก")).to_be_visible()
        page.locator(".hero-bee").screenshot(path=str(OUT / "bee-logo.png"), animations="disabled")
        page.screenshot(path=str(OUT / "home-desktop.png"), full_page=True)
        expect(page.locator("input[type=file]")).to_be_disabled()
        page.get_by_role("checkbox").check()
        expect(page.locator("input[type=file]")).to_be_disabled()
        page.get_by_role("tab", name="สาระสำคัญ", exact=False).click()
        expect(page.locator("input[type=file]")).to_be_enabled()
        page.locator("input[type=file]").set_input_files({"name": "empty.wav", "mimeType": "audio/wav", "buffer": b""})
        expect(page.locator('.upload-panel [role="alert"]')).to_have_text("ไฟล์นี้ว่าง กรุณาเลือกไฟล์เสียงอื่น")
        page.get_by_role("searchbox", name="ค้นหาไฟล์").fill("missing")
        expect(page.get_by_text("ไม่พบไฟล์ที่ค้นหา", exact=True)).to_be_visible()
        page.get_by_role("searchbox", name="ค้นหาไฟล์").fill("")
        page.set_viewport_size({"width": 390, "height": 844})
        page.screenshot(path=str(OUT / "home-mobile.png"), full_page=True)
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        page.emulate_media(reduced_motion="reduce")
        assert page.locator(".hero-bee").evaluate("e=>getComputedStyle(e).animationName") == "none"
        page.set_viewport_size({"width": 1440, "height": 1000})
        page.goto(WEB + "/media/demo")
        page.wait_for_load_state("networkidle")
        print(page.locator("body").inner_text())
        page.get_by_role("tab", name="ไทม์ไลน์การทำ").click()
        expect(page.get_by_role("tab", name="ไทม์ไลน์การทำ")).to_have_attribute("aria-selected", "true")
        page.get_by_role("button", name="สร้างสรุป", exact=True).click()
        expect(page.get_by_role("button", name="สร้างสรุป", exact=True)).to_be_enabled()
        assert requests == [{"template": "timeline", "force": False}]
        page.get_by_role("button", name="แก้ไขข้อความ", exact=True).click()
        page.get_by_role("textbox", name="แก้ไขข้อความ").fill("ฉบับแก้ไขทดสอบ")
        page.get_by_role("button", name="บันทึก", exact=True).click()
        expect(page.get_by_text("ฉบับแก้ไขทดสอบ", exact=True)).to_be_visible()
        assert edited == ["ฉบับแก้ไขทดสอบ"]
        page.screenshot(path=str(OUT / "detail-desktop.png"), full_page=True)
        assert not errors, errors
        print("PASS: consent gating, desktop/mobile layout, template request, transcript edit, no browser runtime errors (mock API)")
    finally:
        browser.close()
