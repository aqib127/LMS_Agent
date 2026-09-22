"""
Expand all collapsible sidebar menus (#sideMenuList_*), then dump
EVERY anchor (visible or hidden) with its href.
"""
from config.settings import settings
from core.auth import ensure_authenticated
from core.browser import browser_session
from core.utils import logger, ensure_dirs


def _try_expand(page, sel: str):
    """Try several strategies to expand a collapsible menu."""
    strategies = [
        f"{sel} >> xpath=..",            # parent
        f"{sel} >> xpath=.. >> css=.caret",
        f"{sel} >> xpath=.. >> css=.arrow",
        f"{sel} >> xpath=.. >> css=.fa-chevron-down",
        f"{sel} >> xpath=.. >> css=.fa-angle-down",
        f"{sel} >> xpath=../span",
        sel,
    ]
    for strat in strategies:
        try:
            loc = page.locator(strat).first
            if loc.count() == 0:
                continue
            loc.click(timeout=1500)
            logger.debug(f"Clicked {strat}")
            return True
        except Exception:
            continue
    return False


def main():
    ensure_dirs()
    with browser_session(use_auth=True, headless=False) as page:
        ensure_authenticated(page)
        page.goto(settings.lms_dashboard_url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(2500)

        # Try to expand each collapsible menu
        for i in range(1, 10):
            sel = f"#sideMenuList_{i}"
            if page.locator(sel).count() == 0:
                continue
            logger.info(f"Trying to expand {sel}")
            _try_expand(page, sel)
            page.wait_for_timeout(800)

        page.wait_for_timeout(1500)

        # Dump ALL anchors, even hidden ones
        print("\n=== ALL ANCHORS ON DASHBOARD (visible AND hidden) ===\n")
        data = page.evaluate(
            """() => {
                const out = [];
                for (const a of document.querySelectorAll('a')) {
                    const text = (a.innerText || a.textContent || '').trim().replace(/\\s+/g, ' ');
                    const href = a.getAttribute('href') || '';
                    // is it visible?
                    const style = window.getComputedStyle(a);
                    const visible = style.display !== 'none' &&
                                    style.visibility !== 'hidden' &&
                                    a.offsetParent !== null;
                    if (!text || !href || href.startsWith('javascript:void')) continue;
                    out.push({ text, href, visible });
                }
                return out;
            }"""
        )
        for row in data:
            flag = "" if row["visible"] else "  [hidden]"
            print(f"{row['text'][:55]:<55}  ->  {row['href']}{flag}")

        print(f"\nTotal anchors: {len(data)}\n")

        # Save the full HTML for offline inspection
        from pathlib import Path
        out = Path("data/snapshots/dashboard_expanded.html")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(page.content(), encoding="utf-8")
        logger.info(f"Saved expanded dashboard HTML to {out.resolve()}")


if __name__ == "__main__":
    main()
