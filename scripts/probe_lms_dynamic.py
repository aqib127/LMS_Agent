"""
Trigger a course selection and capture the network requests.
Uses value-based selection (more reliable than label).
"""
from pathlib import Path
from config.settings import settings
from core.auth import ensure_authenticated
from core.browser import browser_session
from core.utils import logger, ensure_dirs


def _options_with_values(page, sel_id: str) -> list[dict]:
    """Return [{"value": v, "text": t}] for every option."""
    try:
        return page.eval_on_selector_all(
            f"#{sel_id} option",
            """opts => opts.map(o => ({ value: o.value, text: o.textContent.trim() }))"""
        )
    except Exception as e:
        logger.warning(f"Could not read #{sel_id}: {e}")
        return []


def main():
    ensure_dirs()
    captured = []

    with browser_session(use_auth=True, headless=False) as page:
        ensure_authenticated(page)
        page.goto("https://cms.bahria.edu.pk/Sys/Common/GoToLMS.aspx",
                  wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(5000)

        def on_request(req):
            if req.method in ("POST", "GET") and any(
                kw in req.url.lower() for kw in ["assignment", "quiz", "notes",
                                                  "announcement", "lecture", "paper"]
            ):
                captured.append({
                    "method": req.method,
                    "url": req.url,
                    "post_data": req.post_data,
                })

        page.on("request", on_request)

        logger.info("Navigating to Assignments.php")
        page.goto("https://lms.bahria.edu.pk/Student/Assignments.php",
                  wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(2000)

        logger.info("Reading semester options...")
        sems = _options_with_values(page, "semesterId")
        for s in sems[:5]:
            logger.info(f"  semester: value={s['value']!r} text={s['text']!r}")

        # Choose Fall-2026 by text
        target_sem = next((s for s in sems if "Fall-2026" in s["text"]), None)
        if not target_sem:
            raise SystemExit("Could not find Fall-2026 semester")
        logger.info(f"Selecting semester by VALUE: {target_sem['value']!r}")
        page.select_option("#semesterId", value=target_sem["value"])
        page.wait_for_timeout(2500)

        logger.info("Reading course options...")
        courses = _options_with_values(page, "courseId")
        for c in courses[:6]:
            logger.info(f"  course: value={c['value']!r} text={c['text']!r}")

        # Choose the 2nd option (skip "Select Course")
        if len(courses) < 2:
            raise SystemExit("No courses available after selecting semester")
        target = courses[1]
        logger.info(f"Selecting course by VALUE: {target['value']!r} ({target['text']})")

        page.select_option("#courseId", value=target["value"])
        page.wait_for_timeout(5000)

        html = page.content()
        out = Path("data/snapshots/lms/assignments_with_data.html")
        out.write_text(html, encoding="utf-8")
        logger.info(f"Saved {out} ({len(html)} bytes)")

        # Print resulting table rows
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "lxml")
        for i, t in enumerate(soup.find_all("table")):
            rows = t.find_all("tr")
            if len(rows) > 1:
                print(f"\n[table {i}] {len(rows)} rows")
                for r in rows[:6]:
                    cells = [c.get_text(" ", strip=True)[:80]
                             for c in r.find_all(["th", "td"])]
                    print(f"  {cells}")

        page.wait_for_timeout(3000)

        print("\n=== CAPTURED NETWORK REQUESTS ===")
        for c in captured:
            print(f"{c['method']} {c['url']}")
            if c.get("post_data"):
                print(f"    POST: {c['post_data'][:300]}")


if __name__ == "__main__":
    main()
