"""Kiem tra render bang JSON inference that da luu, khong infer lai CPU."""
from pathlib import Path
from playwright.sync_api import sync_playwright


def main():
    folder = Path('outputs/background-check')
    payload = (folder/'result.json').read_text(encoding='utf-8')
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='chrome', headless=True)
        page = browser.new_page(viewport={'width':1440,'height':1000})
        errors=[]
        page.on('pageerror', lambda error: errors.append(str(error)))
        # API da duoc kiem tra bang verify_background_inference.py.
        # Replay dung response that de kiem tra UI, tranh infer lap ~1 phut.
        page.route('**/api/search?*', lambda route: route.fulfill(status=200,content_type='application/json',body=payload))
        page.goto('http://127.0.0.1:8000')
        page.locator('#query-file').set_input_files(str((folder/'gray-background.png').resolve()))
        page.locator('#search-submit').click()
        page.wait_for_selector('.result-card')
        assert page.locator('#search-results .preview-grid img').count()==5
        assert page.locator('.result-card').count()==5
        assert 'Đã tách nền bằng briaai/RMBG-2.0' in page.locator('#search-results').inner_text()
        page.locator('#search-results img').evaluate_all('imgs => Promise.all(imgs.map(i=>i.decode()))')
        page.locator('.query-summary').screenshot(path=str(folder/'web-before-after.png'))
        page.set_viewport_size({'width':390,'height':844})
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        assert not errors, errors
        browser.close()
        print('PASS: actual saved model response renders before/after, alpha, feature mask, contour and 5 results on desktop/mobile')


if __name__=='__main__':
    main()
