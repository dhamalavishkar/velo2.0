"""
Antigravity (AGY) automation tool — opens the Antigravity IDE in browser
and sends a prompt via Playwright CDP.
"""
import logging
import asyncio
from velo_core.tools.base import tool, register_tool
from velo_core.services.browser_pool import browser_pool

logger = logging.getLogger(__name__)

ANTIGRAVITY_URL = "http://localhost:3000"  # or your deployed AGY URL


@tool(
    name="open_antigravity_and_prompt",
    description=(
        "Open the Antigravity IDE in Chrome and type a prompt into the chat input. "
        "Use this when the user wants to code something or asks VELO to delegate to the AI coding assistant."
    ),
    requires_permission=False,
)
async def open_antigravity_and_prompt(prompt: str) -> str:
    try:
        page = await browser_pool.get_page(ANTIGRAVITY_URL)
        await page.wait_for_load_state("networkidle", timeout=10000)

        # Try to find the chat input (AGY-specific selector)
        selectors = [
            'textarea[placeholder*="message"]',
            'textarea[placeholder*="Ask"]',
            'div[contenteditable="true"]',
            'input[type="text"]',
        ]
        chat_input = None
        for sel in selectors:
            try:
                chat_input = await page.wait_for_selector(sel, timeout=2000)
                if chat_input:
                    break
            except Exception:
                continue

        if not chat_input:
            return "Could not find chat input on Antigravity page."

        await chat_input.click()
        await chat_input.fill(prompt)
        await page.keyboard.press("Enter")
        await asyncio.sleep(1)  # Brief wait for response to start
        return f"Prompt sent to Antigravity: {prompt[:80]}..."

    except Exception as e:
        logger.error(f"Antigravity tool error: {e}")
        return f"Error interacting with Antigravity: {str(e)}"


@tool(
    name="google_search",
    description="Search Google for a query and return top results using the browser.",
    requires_permission=False,
)
async def google_search(query: str) -> str:
    try:
        import urllib.parse
        search_url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
        page = await browser_pool.get_page(search_url)
        await page.wait_for_load_state("domcontentloaded", timeout=10000)

        # Extract result snippets
        snippets = await page.evaluate("""
            () => {
                const results = [];
                // Google search result selectors
                const elements = document.querySelectorAll('div.VwiC3b, div.s3v9rd, span.hgKElc');
                for (let el of elements) {
                    const text = el.innerText.trim();
                    if (text && text.length > 30) results.push(text);
                    if (results.length >= 5) break;
                }
                return results;
            }
        """)

        if not snippets:
            # Fallback: get page title and meta description
            title = await page.title()
            return f"Searched for: {query}\nPage: {title}"

        return f"Search results for '{query}':\n\n" + "\n\n".join(
            f"{i+1}. {s}" for i, s in enumerate(snippets)
        )
    except Exception as e:
        logger.error(f"Google search error: {e}")
        return f"Search error: {str(e)}"


for f in [open_antigravity_and_prompt, google_search]:
    register_tool(f)
