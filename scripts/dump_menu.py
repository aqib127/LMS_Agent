"""
Dump all sidebar/menu links from the dashboard with their hrefs.
This tells us what pages we can scrape next.
"""
from config.settings import settings
from core.auth import ensure_authenticated
from core.browser import browser_session
from core.utils import logger, ensure_dirs


def main():
    ensure_dirs()
    with browser_session(use_auth=True, headless=False) as page:
        ensure_authenticated(page)
        logger.info(f"Authenticated. URL: {page.url}")

        page.goto(settings.lms_dashboard_url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(2500)

        logger.info(f"Loaded: {page.url}  |  Title: {page.title()}")

        links = page.locator("a").all()
        seen = set()
        print("\n=== ALL VISIBLE LINKS ON DASHBOARD ===\n")
        for a in links:
            try:
                if not a.is_visible():
                    continue
                href = a.get_attribute("href") or ""
                text = (a.inner_text() or "").strip().replace("\n", " ")
                if not text or not href or href.startswith("javascript:void"):
                    continue
                key = (text, href)
                if key in seen:
                    continue
                seen.add(key)
                print(f"{text[:55]:<55}  ->  {href}")
            except Exception:
                continue
        print(f"\nTotal unique visible links: {len(seen)}\n")


if __name__ == "__main__":
    main()
