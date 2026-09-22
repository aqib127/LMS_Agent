"""Check why quizzes/papers returned 0 items."""
from pathlib import Path
from core.auth import ensure_authenticated
from core.browser import browser_session
from core.utils import logger, ensure_dirs
from scrapers.lms_base import get_semesters, get_courses, fetch_page

def main():
    ensure_dirs()
    with browser_session(use_auth=True, headless=True) as page:
        ensure_authenticated(page)
        page.goto("https://cms.bahria.edu.pk/Sys/Common/GoToLMS.aspx",
                  wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(5000)

        sems = get_semesters(page, "Assignments.php")
        sem = next(s for s in sems if "Fall-2026" in s["label"])
        courses = get_courses(page, "Assignments.php", sem["value"])

        for page_name in ["Quizzes.php", "Papers.php"]:
            print(f"\n===== {page_name} =====")
            for c in courses[:5]:
                html = fetch_page(page, page_name, sem["value"], c["value"])
                # save one for inspection
                if c is courses[0]:
                    out = Path(f"data/snapshots/lms/{page_name.replace('.php','')}_sample.html")
                    out.write_text(html, encoding="utf-8")
                    print(f"  saved sample to {out}")

                from bs4 import BeautifulSoup
                soup = BeautifulSoup(html, "lxml")
                tables = soup.find_all("table")
                for t in tables:
                    rows = t.find_all("tr")
                    if len(rows) > 1:
                        # check first cell of second row
                        cells_text = rows[1].get_text(" ", strip=True)[:100]
                        print(f"  {c['label']:40s}  rows={len(rows)}  first_row={cells_text!r}")
                        break
