"""Read-only navigation QA; no uploads or provider calls."""
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

out = Path(__file__).resolve().parents[1] / 'artifacts' / 'home-icon'
out.mkdir(parents=True, exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, channel='chrome')
    try:
        page = browser.new_page()
        page.goto('http://localhost:3210/')
        page.wait_for_load_state('networkidle')
        print(page.locator('nav').inner_text())
        home = page.get_by_role('link', name='Home · หน้าแรก', exact=True)
        for width in (320, 390, 481, 1280):
            page.set_viewport_size({'width': width, 'height': 672})
            page.evaluate('scrollTo(0,0)')
            expect(home).to_be_visible()
            assert home.inner_text().strip() == ''
            box = home.bounding_box()
            other = page.get_by_role('link', name='ไฟล์ของคุณ', exact=True).bounding_box()
            assert box['width'] >= 44 and box['height'] >= 44
            assert box['x'] > other['x']
            assert box['x'] + box['width'] <= width
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            page.locator('header.masthead').screenshot(path=str(out / f'header-{width}.png'))
        page.get_by_role('link', name='ไฟล์ของคุณ', exact=True).click()
        page.wait_for_url('http://localhost:3210/#files')
        home.click()
        page.wait_for_url('http://localhost:3210/')
        print('PASS: icon-only Home, rightmost position, 44px target, four viewport sizes, navigation')
    finally:
        browser.close()
