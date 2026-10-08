"""Read-only browser check against the real isolated Docker preview."""
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

out = Path(__file__).resolve().parents[1] / "artifacts"
out.mkdir(exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, channel="chrome")
    try:
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        errors = []
        responses = {}
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("response", lambda r: responses.update({r.url: r.status}))
        page.goto("http://localhost:3210")
        page.wait_for_load_state("networkidle")
        print(page.locator("body").inner_text())
        expect(page.get_by_role("heading", name="ไฟล์ของคุณ")).to_be_visible()
        assert responses.get("http://localhost:8210/health") == 200, responses
        assert responses.get("http://localhost:8210/api/media") == 200, responses
        assert not errors, errors
        page.screenshot(path=str(out / "docker-preview.png"), full_page=True)
        print("PASS: Docker web -> real API health/list, no runtime errors")
    finally:
        browser.close()
