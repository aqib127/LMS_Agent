"""
Follow Go To LMS and see where we land. Save HTML snapshots of the LMS home page.
"""
from pathlib import Path
from config.settings import settings
from core.auth import ensure_authenticated
from core.browser import browser_session
from core.utils import logger, ensure_dirs


def main():
    ensure_dirs()
    with browser_session(use_auth=True, headless=False) as page:
        ensure_authenticated(page)

        lms_url = "https://cms.bahria.edu.pk/Sys/Common/GoToLMS.aspx"
        logger.info(f"Navigating to {lms_url}")
        page.goto(lms_url, wait_until="domcontentloaded", timeout=30000)

        # Follow any redirects / meta refreshes
        page.wait_for_timeout(5000)
        for _ in range(5):
            try:
                page.wait_for_load_state("networkidle", timeout=5000)
            except Exception:
                pass
            page.wait_for_timeout(1000)

        final = page.url
        title = page.title()
        logger.info(f"FINAL URL: {final}")
        logger.info(f"TITLE: {title}")

        # Save HTML
        out = Path("data/snapshots/lms_home.html")
        out.write_text(page.content(), encoding="utf-8")
        logger.info(f"Saved {out} ({out.stat().st_size} bytes)")

        # Body preview
        body = page.locator("body").inner_text()[:2000]
        print("\n=== BODY PREVIEW ===")
        print(body)
        print("\n=== END PREVIEW ===\n")

        # Link dump
        print("\n=== ALL VISIBLE LINKS ===")
        seen = set()
        for a in page.locator("a").all():
            try:
                if not a.is_visible():
                    continue
                href = a.get_attribute("href") or ""
                text = (a.inner_text() or "").strip().replace("\n", " ")[:60]
                if not text or not href or href.startswith("javascript:void"):
                    continue
                key = (text, href)
                if key in seen:
                    continue
                seen.add(key)
                print(f"{text:<60}  ->  {href}")
            except Exception:
                continue
        print(f"\nTotal unique links: {len(seen)}")


if __name__ == "__main__":
    main()
