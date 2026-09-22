"""
Force-test the auto-login path (ignores data/auth.json).

Usage:
    python -m scripts.test_login              # headless (default)
    python -m scripts.test_login --headful    # see it happen
"""
import sys
from config.settings import settings
from core.auth import ensure_authenticated, AuthError
from core.browser import browser_session
from core.utils import logger, ensure_dirs


def main():
    ensure_dirs()
    headful = "--headful" in sys.argv

    with browser_session(use_auth=False, headless=not headful) as page:
        try:
            ensure_authenticated(page)
            logger.info("=" * 60)
            logger.info("AUTO-LOGIN WORKED")
            logger.info(f"Final URL: {page.url}")
            logger.info(f"Page title: {page.title()}")
            body = page.locator("body").inner_text()[:300]
            logger.info(f"Body preview:\n{'-'*60}\n{body}\n{'-'*60}")
        except AuthError as e:
            logger.error("=" * 60)
            logger.error(f"AUTO-LOGIN FAILED: {e}")
            logger.error("Run `python -m scripts.test_login --headful` to watch what happens.")
            sys.exit(1)


if __name__ == "__main__":
    main()
