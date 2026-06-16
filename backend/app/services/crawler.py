import logging
from urllib.parse import quote_plus

from app.core.config import settings

logger = logging.getLogger(__name__)

# 常用浏览器 UA 池
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
]

# 按站点匹配地区语言
_SITE_LOCALE_MAP = {
    "US": "en-US",
    "EG": "ar-EG",
    "AE": "ar-AE",
    "SA": "ar-SA",
    "GB": "en-GB",
    "DE": "de-DE",
    "FR": "fr-FR",
    "IT": "it-IT",
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
            await page.wait_for_timeout(3000)

            results = await page.evaluate("""() => {
                const results = [];
                const seen = new Set();

                // 策略：找所有带 /dp/{ASIN} 的链接（Amazon 不变的 URL 结构）
                const links = document.querySelectorAll('a[href*="/dp/"]');
                for (const link of links) {
                    const href = link.href || link.getAttribute('href') || '';
                    const asinMatch = href.match(/\\/dp\\/([A-Z0-9]{10})/);
                    if (!asinMatch || seen.has(asinMatch[1])) continue;
                    seen.add(asinMatch[1]);

                    // 提取标题：从链接所在区域向上查找
                    let title = '';

                    // 1) 在搜索结果卡片内找 h2
                    const card = link.closest('[data-component-type="s-search-result"]');
                    if (card) {
                        const h2 = card.querySelector('h2');
                        if (h2) {
                            // 清理装饰元素
                            for (const tag of h2.querySelectorAll('[role="img"], .a-icon, .a-price')) {
                                tag.remove();
                            }
                            title = h2.textContent.trim();
                        }
                    }

                    // 2) 通用回退：找最近的 h2
                    if (!title) {
                        let el = link;
                        for (let i = 0; i < 10; i++) {
                            el = el.parentElement;
                            if (!el) break;
                            const h2 = el.querySelector('h2');
                            if (h2) {
                                title = h2.textContent.trim();
                                break;
                            }
                        }
                    }

                    // 3) 继续回退：用 aria-label 或链接自身文本
                    if (!title) {
                        title = link.getAttribute('aria-label') || '';
                    }
                    if (!title) {
                        title = link.textContent.trim();
                    }

                    // 4) 最后回退：alt 属性
                    if (!title) {
                        const img = link.querySelector('img');
                        if (img) title = img.getAttribute('alt') || '';
                    }

                    if (title && title.length > 3) {
                        // 截掉 ? 后面的追踪参数
                        const cleanUrl = href.split('?')[0];
                        results.push({
                            asin: asinMatch[1],
                            title: title,
                            url: cleanUrl
                        });
                    }
                }

                return results.slice(0, 48);
            }""")

            await browser.close()
            logger.info("Extracted %d search results via Playwright", len(results))
            return results

    except Exception as e:
        logger.error("Playwright search failed for %s: %s", url, e)
        return []


async def take_screenshot(url: str) -> bytes | None:
    """用 Playwright 打开页面并截图"""
    try:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            launch_args = {"headless": False}
            if settings.crawler_browser_channel:
                launch_args["channel"] = settings.crawler_browser_channel
            launch_args["args"] = ["--no-sandbox", "--start-maximized"]
            browser = await p.chromium.launch(**launch_args)
            context = await browser.new_context(
                viewport={"width": 1280, "height": 900},
                user_agent=USER_AGENTS[0],
            )
            page = await context.new_page()

            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            # 等主要商品内容渲染
            await page.wait_for_timeout(2000)

            screenshot = await page.screenshot(full_page=False, type="png")
            await browser.close()
            return screenshot
    except Exception as e:
        logger.error("Screenshot failed for %s: %s", url, e)
        return None
