import logging
import random
from urllib.parse import quote_plus, urlparse

from app.core.config import settings

logger = logging.getLogger(__name__)

# 搜索结果的 JS 提取脚本（复用，避免重复）
_EXTRACT_SEARCH_RESULTS_JS = """() => {
    const results = [];
    const seen = new Set();
    const links = document.querySelectorAll('a[href*="/dp/"]');
    for (const link of links) {
        const href = link.href || link.getAttribute('href') || '';
        const asinMatch = href.match(/\\/dp\\/([A-Z0-9]{10})/);
        if (!asinMatch || seen.has(asinMatch[1])) continue;
        seen.add(asinMatch[1]);
        let title = '';
        const card = link.closest('[data-component-type="s-search-result"]');
        if (card) {
            const h2 = card.querySelector('h2');
            if (h2) {
                for (const tag of h2.querySelectorAll('[role="img"], .a-icon, .a-price')) {
                    tag.remove();
                }
                title = h2.textContent.trim();
            }
        }
        if (!title) {
            let el = link;
            for (let i = 0; i < 10; i++) {
                el = el.parentElement;
                if (!el) break;
                const h2 = el.querySelector('h2');
                if (h2) { title = h2.textContent.trim(); break; }
            }
        }
        if (!title) { title = link.getAttribute('aria-label') || ''; }
        if (!title) { title = link.textContent.trim(); }
        if (!title) {
            const img = link.querySelector('img');
            if (img) title = img.getAttribute('alt') || '';
        }
        if (title && title.length > 3) {
            results.push({ asin: asinMatch[1], title: title, url: href.split('?')[0] });
        }
    }
    return results.slice(0, 48);
}"""


def _parse_proxy(site_code: str | None = None) -> dict | None:
    """
    解析代理配置（按站点优先）。

    优先顺序：
        1. proxy_map 中匹配 site_code（JSON 格式，如 {"US": "http://1.2.3.4:7890"}）
        2. proxy_server 全局代理
        3. 都不配 → None（直连）
    """
    import json as _json

    proxy_url = ""

    # 1) 按站点匹配
    if site_code and settings.proxy_map.strip():
        try:
            proxy_map = _json.loads(settings.proxy_map)
            proxy_url = proxy_map.get(site_code, "")
        except _json.JSONDecodeError:
            logger.warning("Invalid proxy_map JSON, falling back to proxy_server")

    # 2) 回退到全局代理
    if not proxy_url:
        proxy_url = settings.proxy_server.strip()

    if not proxy_url:
        return None

    parsed = urlparse(proxy_url)
    proxy = {"server": f"{parsed.scheme}://{parsed.hostname}:{parsed.port or 8080}"}
    if parsed.username:
        proxy["username"] = parsed.username
    if parsed.password:
        proxy["password"] = parsed.password
    logger.info("Proxy for %s: %s", site_code or "default", proxy["server"])
    return proxy

# 常用浏览器 UA 池
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36"
]

# 按站点匹配地区语言
_SITE_LOCALE_MAP = {
    "US": "en-US",
    "DE": "de-DE",
    "FR": "fr-FR",
    "ES": "es-ES",
    "JP": "ja-JP",
}
_DEFAULT_LOCALE = "en-US"


def _build_search_url(website: str, root_word: str) -> str:
    """拼接搜索 URL"""
    base = website.rstrip("/")
    query = quote_plus(root_word)
    return f"{base}/s?k={query}"


async def search_amazon(website: str, root_word: str, site_code: str | None = None) -> list[dict]:
    """
    在 Amazon 站点搜索 root_word，返回商品列表。

    使用 Playwright 浏览器加载页面并自适应提取（不依赖 CSS 选择器）。

    Returns:
        [{asin, title, url}, ...]
    """
    url = _build_search_url(website, root_word)
    logger.info("Searching: %s", url)

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        logger.error("Playwright not installed")
        return []

    try:
        async with async_playwright() as p:
            launch_args: dict = {"headless": True, "args": ["--no-sandbox"]}
            if settings.crawler_browser_channel:
                launch_args["channel"] = settings.crawler_browser_channel

            proxy = _parse_proxy(site_code)
            if proxy:
                launch_args["proxy"] = proxy
            browser = await p.chromium.launch(**launch_args)
            locale = _SITE_LOCALE_MAP.get(site_code or "US", _DEFAULT_LOCALE)
            context = await browser.new_context(
                viewport={"width": 1280, "height": 900},
                user_agent=USER_AGENTS[0],
                locale=locale,
            )
            page = await context.new_page()

            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            # 等待搜索结果渲染
            await page.wait_for_timeout(2000)

            results = await page.evaluate(_EXTRACT_SEARCH_RESULTS_JS)

            await browser.close()
            logger.info("Extracted %d search results via Playwright", len(results))
            return results

    except Exception as e:
        logger.error("Playwright search failed for %s: %s", url, e)
        return []


async def take_screenshot(url: str, site_code: str | None = None) -> bytes | None:
    """用 Playwright 打开页面并截图"""
    try:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            launch_args = {"headless": True}
            if settings.crawler_browser_channel:
                launch_args["channel"] = settings.crawler_browser_channel
            launch_args["args"] = ["--no-sandbox", "--start-maximized"]
            proxy = _parse_proxy(site_code)
            if proxy:
                launch_args["proxy"] = proxy
            browser = await p.chromium.launch(**launch_args)
            context = await browser.new_context(
                viewport={"width": 1280, "height": 900},
                user_agent=USER_AGENTS[0],
            )
            page = await context.new_page()

            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            # 等主要商品内容渲染
            await page.wait_for_timeout(1500)

            screenshot = await page.screenshot(full_page=False, type="png")
            await browser.close()
            return screenshot
    except Exception as e:
        logger.error("Screenshot failed for %s: %s", url, e)
        return None


async def crawl_amazon(
    website: str,
    root_word: str,
    site_code: str | None = None,
    keywords_str: str = "",
) -> tuple[list[dict], dict | None, bytes | None]:
    """
    一次浏览器会话完成：搜索 + 关键词匹配 + 截图。

    Args:
        website: Amazon 站点 URL
        root_word: 搜索词
        site_code: 站点代码（US/JP 等）
        keywords_str: 逗号分隔的关键词，用于匹配

    Returns:
        (search_results, matched_dict_or_None, screenshot_bytes_or_None)
    """
    from app.services.matcher import match_keywords  # local import

    search_url = _build_search_url(website, root_word)
    logger.info("Crawling: %s", search_url)

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        logger.error("Playwright not installed")
        return [], None, None

    try:
        async with async_playwright() as p:
            # 反检测参数：隐藏自动化标志
            stealth_args = [
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
            ]
            launch_args: dict = {"headless": True, "args": stealth_args}
            if settings.crawler_browser_channel:
                launch_args["channel"] = settings.crawler_browser_channel
            proxy = _parse_proxy(site_code)
            if proxy:
                launch_args["proxy"] = proxy

            browser = await p.chromium.launch(**launch_args)
            locale = _SITE_LOCALE_MAP.get(site_code or "US", _DEFAULT_LOCALE)
            # 随机挑选 UA，避免指纹一致
            ua = random.choice(USER_AGENTS)
            context = await browser.new_context(
                viewport={"width": 1280, "height": 900},
                user_agent=ua,
                locale=locale,
            )
            page = await context.new_page()

            # ── Step 1: 搜索 ──
            await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(2000)
            search_results = await page.evaluate(_EXTRACT_SEARCH_RESULTS_JS)
            logger.info("Search returned %d results", len(search_results))

            # ── Step 2: 匹配 ──
            matched = match_keywords(keywords_str, search_results)

            # ── Step 3: 截图 ──
            if matched and matched.get("url"):
                target_url = matched["url"]
            else:
                target_url = search_url

            # 只在需要跳转时才导航（命中=详情页，未命中=当前搜索页不需要跳）
            if target_url != search_url:
                await page.goto(target_url, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(1500)

            screenshot = await page.screenshot(full_page=False, type="png")

            await browser.close()
            logger.info(
                "Crawl done: %d results, matched=%s, screenshot=%d bytes",
                len(search_results),
                matched.get("matched_keyword") if matched else "none",
                len(screenshot) if screenshot else 0,
            )
            return search_results, matched, screenshot

    except Exception as e:
        logger.error("crawl_amazon failed for %s: %s", search_url, e)
        return [], None, None
