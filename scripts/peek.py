"""
Usage:
    python -m scripts.peek                          # opens LMS dashboard URL
    python -m scripts.peek <URL>                    # opens given URL
    python -m scripts.peek <URL> --headful          # visible browser
    python -m scripts.peek <URL> --save out.html    # save raw HTML
"""
import sys
from pathlib import Path
from config.settings import settings
from core.browser import browser_session
from core.utils import logger, ensure_dirs


def main():
    ensure_dirs()
    args = sys.argv[1:]
    headful = "--headful" in args
    if headful:
        args.remove("--headful")

    save_to = None
    if "--save" in args:
        i = args.index("--save")
        save_to = args[i + 1]
        del args[i:i + 2]

    url = args[0] if args else settings.lms_dashboard_url

    with browser_session(use_auth=True, headless=not headful) as page:
        logger.info(f"Navigating to {url}")
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(1500)

        title = page.title()
        final_url = page.url
        body_text = page.locator("body").inner_text()[:500]
        html = page.content()

        logger.info(f"Final URL: {final_url}")
        logger.info(f"Title: {title}")
        logger.info(f"Body preview:\n{'-'*60}\n{body_text}\n{'-'*60}")

        if save_to:
            out = Path(save_to)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(html, encoding="utf-8")
            logger.info(f"Saved HTML to {out.resolve()} ({len(html)} bytes)")


if __name__ == "__main__":
    main()
