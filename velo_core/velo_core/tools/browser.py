import logging
from typing import Optional
from velo_core.tools.base import tool, register_tool
from velo_core.services.browser_pool import browser_pool

logger = logging.getLogger(__name__)


@tool(
    name="open_url",
    description="Open a URL in the connected Chrome browser",
    requires_permission=False,
)
async def open_url(url: str) -> str:
    page = await browser_pool.get_page(url)
    return f"Opened {url}. Title: {await page.title()}"


@tool(
    name="click_element",
    description="Click an element on the current page using CSS selector",
    requires_permission=False,
)
async def click_element(selector: str) -> str:
    page = await browser_pool.get_page()
    await page.click(selector)
    return f"Clicked element: {selector}"


@tool(
    name="type_text",
    description="Type text into an input field using CSS selector",
    requires_permission=False,
)
async def type_text(selector: str, text: str) -> str:
    page = await browser_pool.get_page()
    await page.fill(selector, text)
    return f"Typed text into {selector}"


@tool(
    name="extract_text",
    description="Extract text content from an element or the whole page",
    requires_permission=False,
)
async def extract_text(selector: Optional[str] = None) -> str:
    page = await browser_pool.get_page()
    if selector:
        element = await page.query_selector(selector)
        if element:
            text = await element.inner_text()
            return text
        return f"Element not found: {selector}"
    else:
        text = await page.inner_text("body")
        return text[:5000]


@tool(
    name="navigate_back",
    description="Navigate back in browser history",
    requires_permission=False,
)
async def navigate_back() -> str:
    page = await browser_pool.get_page()
    await page.go_back()
    return "Navigated back"


@tool(
    name="navigate_forward",
    description="Navigate forward in browser history",
    requires_permission=False,
)
async def navigate_forward() -> str:
    page = await browser_pool.get_page()
    await page.go_forward()
    return "Navigated forward"


# Register all tools
for tool_func in [open_url, click_element, type_text, extract_text, navigate_back, navigate_forward]:
    register_tool(tool_func)