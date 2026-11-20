"""QA muc 4 tren Chrome co san; server local cong 8000 dang chay."""
import json
from pathlib import Path
import cv2
from playwright.sync_api import sync_playwright


def main():
    output = Path('outputs/web-check')
    output.mkdir(parents=True, exist_ok=True)
    source = next(Path('data/images').glob('*.png'))
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='chrome', headless=True)
        page = browser.new_page(viewport={'width': 1440, 'height': 1000})
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.goto('http://127.0.0.1:8000')
        page.wait_for_selector('.card')
        page.wait_for_selector('.weight-grid')
        page.wait_for_selector('#download-evaluation')
        # Bo model cho luong hoi quy anh dataset da co nen trang.
        page.locator('#remove-background').uncheck()
        page.locator('#query-file').set_input_files(str(source.resolve()))
        with page.expect_response(lambda r: '/api/search?' in r.url) as response:
            page.locator('#search-submit').click()
        assert response.value.status == 200
        page.wait_for_selector('.result-card')
        with page.expect_download() as event:
            page.locator('#download-search').click()
        event.value.save_as(str(output / 'search-result.json'))
        data = json.loads((output / 'search-result.json').read_text(encoding='utf-8'))
        assert page.locator('.result-card').count() == 5
        assert data['excluded_identical'] == 1
        assert data['query']['path'] not in [r['path'] for r in data['results']]
        assert [r['distance'] for r in data['results']] == sorted(r['distance'] for r in data['results'])
        for key in data['dimensions']:
            page.locator('#compare-group').select_option(key)
            assert page.locator('#compare-values details').count() == 6
        page.locator('.result-card details').first.locator('summary').click()
        page.locator('.result-card img').evaluate_all('imgs => Promise.all(imgs.map(i=>i.decode()))')
        page.locator('#search-results').screenshot(path=str(output / 'retrieval.png'))
        with page.expect_download() as download:
            page.locator('#download-search').click()
        download.value.save_as(str(output / 'search-result.json'))
        saved = json.loads((output / 'search-result.json').read_text(encoding='utf-8'))
        assert saved['results'][0]['components']
        page.locator('.result-image').first.click()
        page.wait_for_selector('#query-this-image')
        page.locator('#query-this-image').click()
        page.wait_for_selector('.result-card')
        # Upload moi: JPEG co kich thuoc khac; xac nhan quy trinh letterbox.
        image = cv2.imread(str(source))
        small = cv2.resize(image, (480, 240))
        raw = cv2.imencode('.jpg', small)[1].tobytes()
        page.locator('#query-file').set_input_files({'name':'new-query.jpg','mimeType':'image/jpeg','buffer':raw})
        with page.expect_response(lambda r: '/api/search?' in r.url) as response:
            page.locator('#search-submit').click()
        assert response.value.status == 200
        page.wait_for_selector('.result-card')
        with page.expect_download() as event:
            page.locator('#download-search').click()
        event.value.save_as(str(output / 'fresh-search-result.json'))
        fresh = json.loads((output / 'fresh-search-result.json').read_text(encoding='utf-8'))
        assert fresh['preparation']['letterboxed']
        assert fresh['excluded_identical'] == 0
        assert len(fresh['results']) == 5
        page.wait_for_selector('.result-card')
        page.set_viewport_size({'width':390,'height':844})
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        page.locator('#search-results').screenshot(path=str(output / 'retrieval-mobile.png'))
        page.locator('#query-file').set_input_files({'name':'invalid.png','mimeType':'image/png','buffer':b'invalid'})
        page.locator('#search-submit').click()
        page.wait_for_function("document.querySelector('#query-message').className==='error'")
        assert not page.locator('#search-submit').is_disabled()
        assert not errors, errors
        browser.close()
        print('PASS: upload, fresh resized JPEG, 5 ranks, exact self exclusion, score explanation, all vectors, download, dataset query, bad image, mobile, no JS errors')


if __name__ == '__main__':
    main()
