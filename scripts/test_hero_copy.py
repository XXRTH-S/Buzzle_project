"""Read-only responsive checks for the homepage hero and footer."""
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome", headless=True)
    page = browser.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    for width in (375, 484, 1440):
        page.set_viewport_size({"width": width, "height": 900})
        page.goto("http://localhost:3210/", wait_until="networkidle")
        expect(page.locator(".hero p.eyebrow")).to_have_text("เปลี่ยนเสียงเป็นสรุป ในแบบที่คุณเลือก")
        expect(page.locator("footer")).to_contain_text("เก็บเสียงไว้ ทบทวนประเด็นได้ทุกเมื่อ")
        highlight = page.locator(".highlight")
        expect(highlight).to_have_text("ให้จดจำ")
        assert highlight.evaluate("el => getComputedStyle(el).borderTopLeftRadius") == "999px"
        assert highlight.evaluate("el => getComputedStyle(el).backgroundColor") == "rgb(255, 228, 138)"
        assert highlight.evaluate("el => { const r = document.createRange(); r.selectNodeContents(el); const t = r.getBoundingClientRect(); const b = el.getBoundingClientRect(); return t.left >= b.left && t.right <= b.right && t.top >= b.top && t.bottom <= b.bottom; }")
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        Path("artifacts").mkdir(exist_ok=True)
        page.screenshot(path=f"artifacts/hero-copy-{width}.png")
    assert not errors, errors
    browser.close()
    print("PASS: hero highlight, copy, responsive overflow and runtime errors at 375/484/1440px")
