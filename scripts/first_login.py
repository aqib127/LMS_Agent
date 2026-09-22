"""
Run this ONCE to save your LMS session to data/auth.json.
After this, all scrapers can reuse the session without logging in again.
"""
from config.settings import settings
from core.browser import interactive_browser, AUTH_FILE
from core.utils import logger, ensure_dirs

def main():
    ensure_dirs()
    logger.info("Opening browser to LMS login page...")
    logger.info(f"URL: {settings.lms_login_url}")
    logger.info("Log in manually in the browser window.")
    logger.info("When you are logged in and see your dashboard, come back here and press Enter.")

    with interactive_browser() as (ctx, page):
        page.goto(settings.lms_login_url, wait_until="domcontentloaded")

        input("\n>>> Press Enter here AFTER you are fully logged in: ")

        # Save cookies + localStorage to disk
        ctx.storage_state(path=str(AUTH_FILE))
        logger.info(f"Session saved to {AUTH_FILE.resolve()}")
        logger.info("You can now close the browser.")

if __name__ == "__main__":
    main()
