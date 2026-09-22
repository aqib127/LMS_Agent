"""
Visit every LMS menu page, save HTML, and print the table structure.
"""
from pathlib import Path
from config.settings import settings
from core.auth import ensure_authenticated
from core.browser import browser_session
from core.utils import logger, ensure_dirs
from bs4 import BeautifulSoup


LMS_BASE = "https://lms.bahria.edu.pk/Student/"

PAGES = {
    "dashboard":       "Dashboard.php",
    "course_outline":  "CourseOutline.php",
    "course_plan":     "CoursePlan.php",
    "lecture_notes":   "LectureNotes.php",
    "assignments":     "Assignments.php",
    "quizzes":         "Quizzes.php",
    "miscellaneous":   "Miscellaneous.php",
    "papers":          "Papers.php",
    "announcements":   "Announcements.php",
    "guidelines":      "Guidelines.php",
}


def _cell_text(c):
    return c.get_text(" ", strip=True).replace("\n", " ")


def _analyze(html: str, name: str) -> None:
    soup = BeautifulSoup(html, "lxml")
    print(f"\n========== {name} ==========")
    title = soup.find("title")
    print(f"Title: {title.get_text(strip=True) if title else 'none'}")

    # Selects / filters
    selects = soup.find_all("select")
    for i, s in enumerate(selects[:3]):
        sid = s.get("id") or s.get("name") or ""
        opts = [o.get_text(strip=True) for o in s.find_all("option")][:5]
        print(f"  <select id={sid!r}> options: {opts}")

    # Tables
    tables = soup.find_all("table")
    for i, t in enumerate(tables):
        tid = t.get("id") or t.get("class") or ""
        rows = t.find_all("tr")
        if not rows:
            continue
        header = [_cell_text(c) for c in rows[0].find_all(["th", "td"])]
        print(f"  [table {i}] id={tid!r} rows={len(rows)}")
        print(f"     header: {header[:10]}")
        for r in rows[1:3]:
            print(f"     data  : {[_cell_text(c) for c in r.find_all(['th','td'])][:10]}")


def main():
    ensure_dirs()
    out_dir = Path("data/snapshots/lms")
    out_dir.mkdir(parents=True, exist_ok=True)

    with browser_session(use_auth=True, headless=True) as page:
        # First, log into CMS
        ensure_authenticated(page)
        # Then go to LMS
        page.goto("https://cms.bahria.edu.pk/Sys/Common/GoToLMS.aspx",
                  wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(5000)
        logger.info(f"LMS dashboard: {page.url}")

        for name, path in PAGES.items():
            url = LMS_BASE + path
            try:
                logger.info(f"Fetching {name}: {url}")
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(2000)
                html = page.content()
                out = out_dir / f"{name}.html"
                out.write_text(html, encoding="utf-8")
                logger.info(f"  saved ({len(html)} bytes) final={page.url}")
                _analyze(html, name)
            except Exception as e:
                logger.error(f"  failed {name}: {e}")


if __name__ == "__main__":
    main()
