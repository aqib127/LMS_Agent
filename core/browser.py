from contextlib import contextmanager
from pathlib import Path
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page
from loguru import logger
from config.settings import settings
from core.utils import ensure_dirs

AUTH_FILE = Path("data/auth.json")

@contextmanager
def browser_session(use_auth: bool = True, headless: bool | None = None):
    """
    Launch Chromium, optionally load a saved session, yield a Page, then clean up.

    use_auth: if True and data/auth.json exists, load it (cookies + localStorage).
    headless: override settings.headless (None = use setting).
    """
    ensure_dirs()
    headless = settings.headless if headless is None else headless

    with sync_playwright() as p:
        browser: Browser = p.chromium.launch(
            headless=headless,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        context_kwargs = {
            "viewport": {"width": 1280, "height": 900},
            "user_agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
            ),
        }
        if use_auth and AUTH_FILE.exists():
            context_kwargs["storage_state"] = str(AUTH_FILE)
            logger.debug(f"Loaded session from {AUTH_FILE}")

        ctx: BrowserContext = browser.new_context(**context_kwargs)
        page: Page = ctx.new_page()

        try:
            yield page
        finally:
            browser.close()
            logger.debug("Browser closed")

@contextmanager
def interactive_browser():
    """Non-headless browser for manual login. Yields (context, page)."""
    ensure_dirs()
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        ctx = browser.new_context(viewport={"width": 1280, "height": 900})
        page = ctx.new_page()
        try:
            yield ctx, page
        finally:
            browser.close()
