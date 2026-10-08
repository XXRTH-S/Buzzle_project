"""Real template catalogue; mocked media and model outputs. No cloud calls."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

OUT = Path(__file__).resolve().parents[1] / "artifacts"
OUT.mkdir(exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, channel="chrome")
    try:
        page = browser.new_page(viewport={"width":1440,"height":1000})
        errors=[]
        page.on("pageerror", lambda e: errors.append(str(e)))
        templates=page.request.get("http://localhost:8210/api/templates").json()
        new=[t for t in templates if t.get("example")]
        assert len(new)==5
        page.goto("http://localhost:3210/#templates")
        page.wait_for_load_state("networkidle")
        print(page.locator("#templates").inner_text())
        for template in new:
            page.get_by_role("tab",name=template["label"],exact=False).click()
            panel=page.get_by_role("tabpanel")
            panel.locator("summary").click()
            expect(panel.get_by_text(template["example"]["headline"],exact=True)).to_be_visible()
            expect(panel.get_by_text("ตัวอย่างสมมติเพื่อแสดงรูปแบบ ไม่ใช่ผลสรุปจากไฟล์ของคุณ")).to_be_visible()
        page.locator("#templates").screenshot(path=str(OUT/"templates-desktop.png"))
        page.set_viewport_size({"width":390,"height":844})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        page.locator("#templates").screenshot(path=str(OUT/"templates-mobile.png"))
        calls=[]
        saved=[]
        def mock(route):
            path=route.request.url.split("/api/media/demo")[-1]
            if path=="": data={"id":"demo","filename":"template-test.wav","status":"done"}
            elif path=="/segments": data=[{"id":1,"idx":0,"start_ms":0,"end_ms":1000,"text":"ข้อมูลทดสอบ","text_model":"ข้อมูลทดสอบ","text_edited":None,"speaker":None}]
            elif path=="/summaries": data=saved
            elif path=="/summarize":
                body=route.request.post_data_json
                calls.append(body["template"])
                tpl=next(t for t in new if t["id"]==body["template"])
                saved.append({"template_id":tpl["id"],"model":"mock","payload":tpl["example"],"usage":{"input_tokens":1,"output_tokens":1,"cache_read_tokens":0}})
                data={"status":"queued","cached":False}
            else: data={}
            route.fulfill(status=200,content_type="application/json",body=json.dumps(data))
        page.route("**/api/media/demo**",mock)
        page.goto("http://localhost:3210/media/demo")
        page.wait_for_load_state("networkidle")
        for template in new:
            page.get_by_role("tab",name=template["label"],exact=False).click()
            page.get_by_role("button",name="สร้างสรุป",exact=True).click()
            expect(page.get_by_role("button",name="สร้างสรุปใหม่",exact=True)).to_be_enabled()
            expect(page.get_by_text(template["example"]["headline"],exact=True).last).to_be_visible()
        assert calls==[t["id"] for t in new]
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        assert not errors,errors
        print("PASS: five real template previews, mobile layout, five selected summary requests and structured results")
    finally:
        browser.close()
