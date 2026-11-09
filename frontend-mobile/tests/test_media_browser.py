"""Browser regressions. Start Vite on 5174, then run pytest on this file.

Uses isolated API/media fixtures; never logs into or writes a real database.
"""
import os
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright, expect

BASE_URL = os.environ.get("MOBILE_TEST_URL", "http://127.0.0.1:5174")


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as pw:
        edge = Path('C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe')
        executable = os.environ.get('BROWSER_EXECUTABLE') or (str(edge) if edge.exists() else None)
        instance = pw.chromium.launch(headless=True, executable_path=executable)
        yield instance
        instance.close()


@pytest.fixture
def page(browser):
    context = browser.new_context(viewport={"width": 390, "height": 844})
    page = context.new_page()
    page.route("**/__media_test", lambda route: route.fulfill(body="<main id='fixture'></main>", content_type="text/html"))
    page.goto(f"{BASE_URL}/__media_test")
    yield page
    context.close()


def test_video_sources_remain_inert_until_explicit_play(page):
    result = page.evaluate("""async () => {
      const { enhanceDetailHtml } = await import('/src/utils/detailHtml.ts');
      const root = document.querySelector('main');
      root.innerHTML = enhanceDetailHtml('<video autoplay preload="auto" src="/uploads/a.mp4"><source src="/uploads/b.webm" type="video/webm"></video>');
      return {src: root.querySelector('video').getAttribute('src'),
        nested: root.querySelector('source').getAttribute('src'),
        autoplay: root.querySelector('video').autoplay,
        play: root.querySelector('button')?.textContent};
    }""")
    assert result["src"] is None
    assert result["nested"] is None
    assert result["autoplay"] is False
    assert result["play"] == "播放视频"


def test_detail_responsive_images_preserve_original_and_reserve_dimensions(page):
    result = page.evaluate("""async () => {
      const { enhanceDetailHtml } = await import('/src/utils/detailHtml.ts');
      const html = enhanceDetailHtml('<p>商品图片</p><img src="/uploads/a.jpg" alt="商品"><img src="/uploads/b.jpg">', {
        '/uploads/a.jpg': {original:'/uploads/a.jpg', width:2000, height:1500,
          images:[{url:'/uploads/_media/a-720.webp',width:720,height:540,bytes:1000},
                  {url:'/uploads/_media/a-1080.webp',width:1080,height:810,bytes:2000}]}});
      const doc = new DOMParser().parseFromString(html,'text/html');
      return {images:[...doc.images].map(i=>({loading:i.loading,original:i.dataset.original,
        width:i.width,height:i.height,priority:i.getAttribute('fetchpriority')})),
        srcset:doc.querySelector('source')?.getAttribute('srcset')};
    }""")
    assert result["images"][0] == {"loading": "eager", "original": "/uploads/a.jpg", "width": 2000, "height": 1500, "priority": "high"}
    assert result["images"][1]["loading"] == "lazy"
    assert "720w" in result["srcset"] and "1080w" in result["srcset"]


def test_preview_uses_original_instead_of_thumbnail(page):
    page.evaluate("""async () => {
      const { attachDetailImageClicks } = await import('/src/utils/detailHtml.ts');
      document.querySelector('main').innerHTML = '<img src="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7" data-original="/uploads/full.jpg">';
      attachDetailImageClicks(document.querySelector('main'), url => window.previewUrl=url);
      document.querySelector('img').click();
    }""")
    assert page.evaluate("window.previewUrl") == "/uploads/full.jpg"


def test_details_visible_while_title_and_reviews_pending(page):
    pending = []
    page.add_init_script("localStorage.setItem('bm_mobile_visitor_key_v2','media-test-visitor')")

    def api(route):
        path = route.request.url.split("?")[0]
        if path.endswith("/home-page") or path.endswith("/messages"):
            pending.append(route)
        elif path.endswith("/products/1"):
            route.fulfill(json={"data": {"id": 1, "name": "测试商品", "status": "on", "price": 10, "starRating": 0, "detailHtml": "<p>详情已就绪</p>"}})
        else:
            route.fulfill(json={"data": {}})

    page.route(f"{BASE_URL}/api/**", api)
    page.goto(f"{BASE_URL}/products/1", wait_until="domcontentloaded")
    expect(page.get_by_role("heading", name="测试商品")).to_be_visible(timeout=4000)
    expect(page.get_by_text("详情已就绪")).to_be_visible()
    for route in pending:
        route.fulfill(json={"data": {"items": [], "mobileTitle": "商品列表"}})


def test_media_binding_occurs_after_detail_mount(page):
    page.add_init_script("localStorage.setItem('bm_mobile_visitor_key_v2','media-test-visitor')")
    page.route(f"{BASE_URL}/api/**", lambda route: route.fulfill(json={"data": {
        "id": 1, "name": "测试商品", "status": "on", "price": 10, "starRating": 0,
        "detailHtml": '<img width="120" height="90" src="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7">', "items": []}}))
    page.goto(f"{BASE_URL}/products/1")
    page.locator(".pd__html img").click()
    expect(page.get_by_role("dialog", name="图片预览")).to_be_visible()


def test_video_quality_selection_does_not_download_before_play_and_retry_is_available(page):
    requested = []
    page.route("**/uploads/**", lambda route: (requested.append(route.request.url), route.fulfill(status=404)))
    page.evaluate("""async () => {
      const { prepareDetailMedia, attachDeferredMedia } = await import('/src/utils/detailMedia.ts');
      const root = document.querySelector('main');
      root.innerHTML = prepareDetailMedia('<video src="/uploads/original.mp4"></video>', {
        '/uploads/original.mp4':{original:'/uploads/original.mp4',width:1280,height:720,
          videos:[{url:'/uploads/low.mp4',width:854,height:480,bytes:1000,label:'low'},
                  {url:'/uploads/hd.mp4',width:1280,height:720,bytes:2000,label:'hd'}]}});
      window.cleanupMedia=attachDeferredMedia(root);
    }""")
    page.get_by_label("视频清晰度").select_option("/uploads/hd.mp4")
    page.wait_for_timeout(200)
    assert requested == []
    page.get_by_role("button", name="播放视频").click()
    expect(page.get_by_role("button", name="重试播放")).to_be_enabled(timeout=5000)
    assert any(url.endswith("/hd.mp4") for url in requested)
    assert any(url.endswith("/original.mp4") for url in requested)
    page.evaluate("window.cleanupMedia()")
    assert page.locator("video").get_attribute("src") is None


def test_failed_derivative_image_falls_back_to_original(page):
    requested = []
    pixel = bytes.fromhex("47494638396101000100800000000000ffffff21f90401000000002c00000000010001000002024401003b")

    def image_route(route):
        requested.append(route.request.url)
        if route.request.url.endswith(".webp"):
            route.fulfill(status=404)
        else:
            route.fulfill(body=pixel, content_type="image/gif")

    page.route("**/uploads/**", image_route)
    page.evaluate("""async () => {
      const { prepareDetailMedia, attachDeferredMedia } = await import('/src/utils/detailMedia.ts');
      const root=document.querySelector('main');
      root.innerHTML=prepareDetailMedia('<img src="/uploads/full.gif">', {
        '/uploads/full.gif':{original:'/uploads/full.gif',width:320,height:240,
          images:[{url:'/uploads/missing.webp',width:320,height:240,bytes:1000}]}});
      attachDeferredMedia(root);
    }""")
    page.wait_for_function("document.querySelector('img').naturalWidth > 0")
    assert any(url.endswith("missing.webp") for url in requested)
    assert any(url.endswith("full.gif") for url in requested)
    assert page.get_by_role("button", name="重新加载图片").count() == 0


def test_exhausted_nested_video_sources_allow_retry(page):
    page.route("**/uploads/**", lambda route: route.fulfill(status=404))
    page.evaluate("""async () => {
      const { prepareDetailMedia, attachDeferredMedia } = await import('/src/utils/detailMedia.ts');
      const root = document.querySelector('main');
      root.innerHTML = prepareDetailMedia('<video><source src="/uploads/failed.mp4" type="video/mp4"><source src="/uploads/failed.webm" type="video/webm"></video>');
      attachDeferredMedia(root);
    }""")
    page.get_by_role("button", name="播放视频").click()
    expect(page.get_by_role("button", name="重试播放")).to_be_enabled(timeout=4000)
    page.get_by_role("button", name="重试播放").click()
    expect(page.get_by_role("button", name="重试播放")).to_be_enabled(timeout=4000)


def test_first_actual_cover_is_prioritized_after_coverless_products(page):
    page.add_init_script("localStorage.setItem('bm_mobile_visitor_key_v2','media-test-visitor')")

    def api(route):
        path = route.request.url.split("?")[0]
        if path.endswith("/products"):
            rows = [{"id": i, "name": f"测试商品{i}", "status": "on", "price": 1} for i in range(3)]
            rows[-1]["coverImage"] = "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"
            route.fulfill(json={"data": {"items": rows, "total": 3}})
        else:
            route.fulfill(json={"data": {"published": False}})

    page.route(f"{BASE_URL}/api/**", api)
    page.goto(f"{BASE_URL}/products")
    cover = page.locator(".prow__cover img").first
    expect(cover).to_have_attribute("loading", "eager")
    expect(cover).to_have_attribute("fetchpriority", "high")


def test_pausing_buffering_video_is_not_reported_as_failure(page):
    held = []
    page.route("**/uploads/held.mp4", lambda route: held.append(route))
    page.evaluate("""async () => {
      const { prepareDetailMedia, attachDeferredMedia }=await import('/src/utils/detailMedia.ts');
      const root=document.querySelector('main');
      root.innerHTML=prepareDetailMedia('<video src="/uploads/held.mp4"></video>');
      window.detachMedia = attachDeferredMedia(root);
    }""")
    try:
        page.get_by_role("button", name="播放视频").click()
        # Exclusive playback of another video uses this same native pause operation.
        page.locator("video").evaluate("v=>v.pause()")
        expect(page.get_by_role("button", name="播放视频")).to_be_enabled(timeout=2000)
        expect(page.get_by_text("视频加载失败", exact=True)).to_have_count(0)
    finally:
        page.evaluate("window.detachMedia()")
        for route in held:
            route.abort()


def test_retry_linked_image_does_not_follow_the_link(page):
    page.route("**/uploads/missing.jpg", lambda route: route.fulfill(status=404))
    page.evaluate("""async () => {
      const { prepareDetailMedia, attachDeferredMedia }=await import('/src/utils/detailMedia.ts');
      const root=document.querySelector('main');
      root.innerHTML=prepareDetailMedia('<a href="#linked-picture"><img src="/uploads/missing.jpg"></a>');
      attachDeferredMedia(root);
    }""")
    page.get_by_role("button", name="重新加载图片").click()
    assert page.url == f"{BASE_URL}/__media_test"
