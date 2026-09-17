import logging
from typing import Optional
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from velo_core.config import get_settings

logger = logging.getLogger(__name__)


class BrowserPool:
    def __init__(self):
        self.settings = get_settings()
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._connected = False

    async def connect(self) -> BrowserContext:
        if self._connected and self._context:
            return self._context

        try:
            self._playwright = await async_playwright().start()
            cdp_url = f"http://localhost:{self.settings.chrome_debug_port}"
            logger.info(f"Connecting to Chrome CDP at {cdp_url}")
            self._browser = await self._playwright.chromium.connect_over_cdp(cdp_url)
            self._context = self._browser.contexts[0] if self._browser.contexts else await self._browser.new_context()
            self._connected = True
            logger.info("Connected to Chrome successfully")
            return self._context
        except Exception as e:
            logger.error(f"Failed to connect to Chrome CDP: {e}")
            raise

    async def get_page(self, url: str | None = None) -> Page:
        context = await self.connect()
        pages = context.pages
        if pages:
            page = pages[0]
            if url:
                await page.goto(url, wait_until="domcontentloaded")
            return page
        page = await context.new_page()
        if url:
            await page.goto(url, wait_until="domcontentloaded")
        return page

    async def close(self):
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        self._connected = False
        logger.info("Browser pool closed")


browser_pool = BrowserPool()