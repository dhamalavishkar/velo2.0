import logging
from typing import Optional
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from velo_core.config import get_settings

logger = logging.getLogger(__name__)


class BrowserPool:
    """
    Manages a persistent connection to an existing Chrome profile via CDP.
    Chrome must be launched with: --remote-debugging-port=9222
    Falls back to launching a fresh Chromium if CDP connection fails.
    """

    def __init__(self):
        self.settings = get_settings()
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._connected = False
        self._mode: str = "none"  # "cdp" | "local" | "none"

    async def connect(self) -> BrowserContext:
        if self._connected and self._context:
            return self._context

        self._playwright = await async_playwright().start()

        # Try CDP first (existing Chrome with sessions)
        cdp_url = f"http://localhost:{self.settings.chrome_debug_port}"
        try:
            logger.info(f"Connecting to Chrome CDP at {cdp_url} ...")
            self._browser = await self._playwright.chromium.connect_over_cdp(cdp_url)
            contexts = self._browser.contexts
            self._context = contexts[0] if contexts else await self._browser.new_context()
            self._connected = True
            self._mode = "cdp"
            logger.info("✅ Connected to existing Chrome via CDP")
            return self._context
        except Exception as e:
            logger.warning(f"CDP failed ({e}). Launching local Chromium...")

        # Fallback: launch headless Chromium (no saved sessions)
        try:
            self._browser = await self._playwright.chromium.launch(headless=False)
            self._context = await self._browser.new_context()
            self._connected = True
            self._mode = "local"
            logger.info("✅ Launched local Chromium (no saved sessions)")
            return self._context
        except Exception as e:
            logger.error(f"Failed to launch Chromium: {e}")
            raise RuntimeError("Browser unavailable — start Chrome with --remote-debugging-port=9222") from e

    async def get_page(self, url: str | None = None) -> Page:
        context = await self.connect()
        pages = context.pages
        page = pages[0] if pages else await context.new_page()
        if url:
            await page.goto(url, wait_until="domcontentloaded", timeout=15000)
        return page

    async def new_page(self, url: str | None = None) -> Page:
        """Open a fresh tab."""
        context = await self.connect()
        page = await context.new_page()
        if url:
            await page.goto(url, wait_until="domcontentloaded", timeout=15000)
        return page

    async def close(self):
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        self._connected = False
        logger.info("Browser pool closed")


browser_pool = BrowserPool()