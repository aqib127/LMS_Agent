"""Open the LMS assignments page and dump row HTML to see if upload links exist."""
import sys
from pathlib import Path
from core.auth import ensure_authenticated
from core.browser import browser_session
from core.utils import logger, ensure_dirs
from scrapers.lms_base import get_semesters, get_courses, fetch_page
from bs4 import BeautifulSoup


def main():
    ensure_dirs()
    with browser_session(use_auth=True, headless=False) as page:
        ensure_authenticated(page)
        page.goto("https://cms.bahria.edu.pk/Sys/Common/GoToLMS.aspx",
                  wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(5000)

        sems = get_semesters(page, "Assignments.php")
        sem = next((s for s in sems if "Fall-2026" in s["label"]), sems[0])
        courses = get_courses(page, "Assignments.php", sem["value"])
        ai_courses = [c for c in courses if "intelligence" in c["label"].lower()]
        if not ai_courses:
            print("No AI Lab course found")
            return
        c = ai_courses[0]

        logger.info(f"Opening assignments for: {c['label']}")
        html = fetch_page(page, "Assignments.php", sem["value"], c["value"])
        soup = BeautifulSoup(html, "lxml")

        # Save the raw HTML
        out = Path("data/snapshots")
        out.mkdir(parents=True, exist_ok=True)
        f = out / "assignments_raw.html"
        f.write_text(html, encoding="utf-8")
        logger.info(f"Saved: {f}")

        # Print the table row for each assignment, plus its links
        for t in soup.find_all("table"):
            rows = t.find_all("tr")
            if len(rows) < 2:
                continue
            print(f"\n=== Table with {len(rows)} rows ===")
            header = [c.get_text(" ", strip=True) for c in rows[0].find_all(["th","td"])]
            print("Header:", header)
            for r in rows[1:]:
                cells = r.find_all(["th","td"])
                txt = [c.get_text(" ", strip=True)[:40] for c in cells]
                print(f"\nRow: {txt}")
                # Print every <a> in this row
                for a in r.find_all("a"):
                    href = (a.get("href") or "").strip()
                    label = a.get_text(" ", strip=True)[:40]
                    if href and not href.lower().startswith("javascript:void"):
                        print(f"    link: '{label}' -> {href}")
                # Print every <form> or <input type=file>
                for inp in r.find_all("input"):
                    print(f"    input: type={inp.get('type')} name={inp.get('name')} id={inp.get('id')}")


if __name__ == "__main__":
    main()
