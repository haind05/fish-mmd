"""Kiem tra UI RMBG khi chua co credential; khong gia lap ket qua model that."""
from pathlib import Path
from playwright.sync_api import sync_playwright


def main():
    source = next(Path('data/images').glob('*.png'))
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='chrome', headless=True)
        page = browser.new_page(viewport={'width':1440,'height':1000})
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto('http://127.0.0.1:8000')
        page.wait_for_function("document.querySelector('#background-status').dataset.state")
        assert page.locator('#remove-background').is_checked()
        state = page.locator('#background-status').get_attribute('data-state')
        if state in ('needs_login','missing_dependencies'):
            page.locator('#query-file').set_input_files(str(source.resolve()))
            page.locator('#search-submit').click()
            page.wait_for_function("document.querySelector('#query-message').className==='error'")
            assert page.locator('.result-card').count() == 0
            assert not page.locator('#search-submit').is_disabled()
            page.screenshot(path='outputs/web-check/background-login.png', full_page=False)
        page.locator('#remove-background').uncheck()
        page.locator('#query-file').set_input_files(str(source.resolve()))
        page.locator('#search-submit').click()
        page.wait_for_selector('.result-card')
        assert page.locator('.result-card').count() == 5
        assert not errors, errors
        browser.close()
        print('PASS: RMBG default selection, actual readiness status, missing-login error without false results, legacy search still works')


if __name__ == '__main__':
    main()
