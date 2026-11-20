"""QA tuy chon: pip install playwright; dung Chrome co san tren Windows."""
from pathlib import Path
from playwright.sync_api import sync_playwright


def main():
    output = Path("outputs/web-check")
    output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000}, device_scale_factor=1)
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto("http://127.0.0.1:8000")
        page.wait_for_selector(".card")
        assert page.locator(".card").count() == 24
        assert page.locator("#images-count").inner_text() == "1.000"
        page.locator("#grid img").evaluate_all("imgs => Promise.all(imgs.map(i=>{i.loading='eager';return i.decode()}))")
        page.screenshot(path=str(output / "gallery.png"), full_page=True)
        page.locator("#next").click()
        page.wait_for_function("document.querySelector('#page-label').textContent.includes('2 /')")
        page.locator("#search").fill("cheilinus")
        page.locator("#filters").evaluate("form => form.requestSubmit()")
        page.wait_for_function("document.querySelector('.card') && [...document.querySelectorAll('.species-name')].every(e=>e.textContent.includes('cheilinus'))")
        page.locator(".card").first.click()
        page.wait_for_selector("#feature-choice")
        for key in ["geometry", "ulbp", "contour_profile", "fourier", "hsv", "color_moments", "spatial_hsv", "glcm"]:
            page.locator("#feature-choice").select_option(key)
            assert page.locator("#chart svg").count() == 1
            assert page.locator("#vector-table tr").count() > 0
        page.locator("#feature-choice").select_option("geometry")
        page.locator("#detail-body img").evaluate_all("imgs => Promise.all(imgs.map(i=>i.decode()))")
        page.screenshot(path=str(output / "detail.png"))
        with page.expect_download() as event:
            page.locator("#download").click()
        download = event.value
        assert download.suggested_filename.endswith(".features.json")
        page.locator("#close-detail").click()
        page.locator("#search").fill("no-such-fish-xyz")
        page.locator("#filters").evaluate("form => form.requestSubmit()")
        page.wait_for_function("document.querySelector('.empty')?.textContent.includes('Không tìm thấy')")
        assert "Không tìm thấy" in page.locator(".empty").inner_text()
        page.locator("#search").fill("")
        page.locator("#filters").evaluate("form => form.requestSubmit()")
        page.wait_for_selector(".card")
        page.locator("#species").select_option("101")
        page.wait_for_function("document.querySelector('.card') && [...document.querySelectorAll('.species-name')].every(e=>e.textContent.includes('cheilinus chlorourus'))")
        assert page.locator(".card").count() == 4
        page.set_viewport_size({"width": 390, "height": 844})
        page.screenshot(path=str(output / "mobile.png"), full_page=True)
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        assert not errors, errors
        browser.close()
        print("PASS: gallery, paging, search, species filter, detail, 8 charts, download, empty results, mobile; no JS errors")


if __name__ == "__main__":
    main()
