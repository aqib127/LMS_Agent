"""
Save HTML snapshots of the newly discovered submenu pages.
"""
from pathlib import Path
from config.settings import settings
from core.auth import ensure_authenticated
from core.browser import browser_session
from core.utils import logger, ensure_dirs

PAGES = {
    "attendance":       "https://cms.bahria.edu.pk/Sys/Student/ClassAttendance/StudentWiseAttendance.aspx",
    "timetable":        "https://cms.bahria.edu.pk/Sys/Student/CourseRegistration/TimeTable.aspx",
    "registered_courses": "https://cms.bahria.edu.pk/Sys/Student/CourseRegistration/RegisteredCourses.aspx",
    "offered_courses":  "https://cms.bahria.edu.pk/Sys/Student/CourseRegistration/OfferedCourses.aspx",
    "exam_result":      "https://cms.bahria.edu.pk/Sys/Student/Exams/ExamResult.aspx",
    "exam_seats":       "https://cms.bahria.edu.pk/Sys/Student/ExamSeatingPlan/ExamSeats",
    "community_services": "https://cms.bahria.edu.pk/Sys/Student/Exams/CommunityServices.aspx",
    "extra_teaching":   "https://cms.bahria.edu.pk/Sys/Student/ExtraTeachingSessions.aspx",
    "fee_challans":     "https://cms.bahria.edu.pk/Sys/Student/FeeManagement/FeeChallans",
}

def main():
    ensure_dirs()
    out_dir = Path("data/snapshots")
    out_dir.mkdir(parents=True, exist_ok=True)

    with browser_session(use_auth=True, headless=True) as page:
        ensure_authenticated(page)
        for name, url in PAGES.items():
            try:
                logger.info(f"Fetching {name}: {url}")
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(2000)
                html = page.content()
                out = out_dir / f"{name}.html"
                out.write_text(html, encoding="utf-8")
                logger.info(f"  saved {out} ({len(html)} bytes) final={page.url}")
            except Exception as e:
                logger.error(f"  failed {name}: {e}")

if __name__ == "__main__":
    main()
