"""Production-bundle media smoke + cold/warm synthetic network comparison.

Run alongside media_fixture.py; artifacts go to ignored output/media-review.
"""
from pathlib import Path
import json
import os
import time
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "output/media-review"
OUT.mkdir(parents=True, exist_ok=True)
BASE = "http://127.0.0.1:5015"


def login(context):
    context.add_init_script("localStorage.setItem('bm_mobile_visitor_key_v2','media-fixture-only')")


with sync_playwright() as pw:
    edge = Path('C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe')
    browser = pw.chromium.launch(headless=True, executable_path=os.environ.get("BROWSER_EXECUTABLE") or (str(edge) if edge.exists() else None))
    results = {"fixture": "synthetic, not production", "network": {"downloadMbps": 1, "latencyMs": 300}, "list": []}
    for mode in ("original", "optimized"):
        context = browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2)
        login(context)
        context.add_cookies([{"name": "media_fixture_mode", "value": mode, "url": BASE}])
        page = context.new_page()
        cdp = context.new_cdp_session(page)
        cdp.send("Network.enable")
        cdp.send("Network.emulateNetworkConditions", {"offline": False, "latency": 300,
            "downloadThroughput": 125000, "uploadThroughput": 125000, "connectionType": "cellular3g"})
        for cache in ("cold", "warm"):
            started = time.perf_counter()
            page.goto(BASE + "/products", wait_until="domcontentloaded")
            page.wait_for_function("document.querySelectorAll('.prow__cover img').length > 0 && [...document.querySelectorAll('.prow__cover img')].slice(0,2).every(i=>i.complete&&i.naturalWidth>0)", timeout=60000)
            elapsed = time.perf_counter() - started
            entries = page.evaluate("performance.getEntriesByType('resource').filter(e=>e.name.includes('/uploads/')).map(e=>({url:e.name,bytes:e.transferSize,encoded:e.encodedBodySize,duration:e.duration}))")
            results["list"].append({"mode": mode, "cache": cache, "firstTwoImagesSeconds": round(elapsed, 3), "media": entries})
            if mode == "optimized":
                assert all("/_media/" in item["url"] for item in entries), entries
            if mode == "optimized" and cache == "warm":
                assert any(item["bytes"] == 0 for item in entries), entries
        if mode == "optimized":
            page.screenshot(path=str(OUT / "list-mobile.png"), full_page=True)
        context.close()

    context = browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2)
    login(context)
    page = context.new_page()
    errors, requests = [], []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("request", lambda req: requests.append(req.url))
    page.goto(BASE + "/products/1", wait_until="networkidle")
    assert not any(".mp4" in url or ".webm" in url for url in requests), requests
    expect(page.get_by_role("button", name="播放视频")).to_be_visible()
    page.screenshot(path=str(OUT / "detail-mobile.png"))
    img = page.locator(".pd__html img").first
    original = img.get_attribute("data-original")
    img.click()
    expect(page.get_by_role("dialog", name="图片预览")).to_be_visible()
    assert page.locator(".pd-lightbox__img").get_attribute("src") == original
    page.get_by_role("button", name="关闭", exact=True).click()
    page.get_by_role("button", name="播放视频").click()
    page.wait_for_function("document.querySelector('video').currentTime > 0.3")
    page.get_by_label("视频清晰度").select_option(index=1)
    page.wait_for_function("document.querySelector('video').currentTime > 0.5 && !document.querySelector('video').paused")
    page.locator("video").evaluate("v=>v.currentTime=2")
    page.wait_for_function("document.querySelector('video').currentTime >= 2 && !document.querySelector('video').seeking")
    page.locator("#pd-review-input").fill("媒体回归测试评价")
    page.get_by_role("button", name="提交评价", exact=True).click()
    expect(page.get_by_text("提交成功，审核通过后将公开展示")).to_be_visible()
    page.get_by_role("button", name="← 返回").click()
    expect(page.locator(".prow").first).to_be_visible()
    assert page.locator("video").count() == 0
    page.get_by_placeholder("搜索商品名称或地址").fill("测试")
    page.get_by_role("button", name="搜索", exact=True).click()
    page.locator(".prow").first.click()
    expect(page.get_by_role("button", name="播放视频")).to_be_visible()
    page.set_viewport_size({"width": 1440, "height": 1000})
    page.wait_for_function("document.querySelector('.pd__html img').complete && document.querySelector('.pd__html img').naturalWidth > 0")
    page.wait_for_load_state("networkidle")
    page.screenshot(path=str(OUT / "detail-desktop.png"))
    page.emulate_media(color_scheme="dark", reduced_motion="reduce")
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    page.get_by_role("button", name="← 返回").click()
    expect(page.get_by_placeholder("搜索商品名称或地址")).to_have_value("测试")
    assert errors == [], errors
    results["smoke"] = {"videoNoPreload": True, "previewOriginal": True, "playSwitchSeek": True,
                        "navigation": True, "reviewSubmission": True, "filterPreservation": True, "consoleErrors": errors}
    context.close()
    browser.close()
    (OUT / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(results, ensure_ascii=True))
