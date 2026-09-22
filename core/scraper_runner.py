"""
Live scraper: logs in, visits each URL, runs the matching scraper,
and stores results in SQLite.
"""
from core.auth import ensure_authenticated
from core.browser import browser_session
from core.storage import init_db, upsert_many, start_run, finish_run
from core.utils import logger, ensure_dirs
from config.settings import settings

from scrapers import (
    scrape_attendance, scrape_courses, scrape_exam_results,
    scrape_fee_challans, scrape_exam_seats, scrape_community_services,
)


# (kind, URL, scraper function)
TARGETS = [
    ("attendance",
     "https://cms.bahria.edu.pk/Sys/Student/ClassAttendance/StudentWiseAttendance.aspx",
     scrape_attendance),

    ("courses",
     "https://cms.bahria.edu.pk/Sys/Student/CourseRegistration/RegisteredCourses.aspx",
     scrape_courses),

    ("exam_results",
     "https://cms.bahria.edu.pk/Sys/Student/Exams/ExamResult.aspx",
     scrape_exam_results),

    ("fees",
     "https://cms.bahria.edu.pk/Sys/Student/FeeManagement/FeeChallans",
     scrape_fee_challans),

    ("exam_seats",
     "https://cms.bahria.edu.pk/Sys/Student/ExamSeatingPlan/ExamSeats",
     scrape_exam_seats),

    ("community_services",
     "https://cms.bahria.edu.pk/Sys/Student/Exams/CommunityServices.aspx",
     scrape_community_services),
]


def scrape_all_live() -> dict[str, dict]:
    """
    Log in, scrape everything, store to DB.
    Returns per-kind summary: {"attendance": {"new": 0, "changed": 0, "total": 10}, ...}
    """
    ensure_dirs()
    init_db()
    run_id = start_run()
    summary = {}

    try:
        with browser_session(use_auth=True, headless=True) as page:
            ensure_authenticated(page)

            for kind, url, parser in TARGETS:
                try:
                    logger.info(f"[{kind}] fetching {url}")
                    page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    page.wait_for_timeout(2000)
                    html = page.content()
                    items = parser(html)
                    new, changed = upsert_many(kind, items)
                    summary[kind] = {
                        "new": new,
                        "changed": changed,
                        "total": len(items),
                    }
                    logger.info(
                        f"[{kind}] {len(items)} items ({new} new, {changed} changed)"
                    )
                except Exception as e:
                    logger.error(f"[{kind}] failed: {e}")
                    summary[kind] = {"error": str(e)}

        finish_run(run_id, "ok")
        return summary

    except Exception as e:
        finish_run(run_id, "failed", str(e))
        raise
