"""
Deep LMS scrape: for every course in the current semester,
fetch assignments, quizzes, notes, announcements, papers.
"""
from core.auth import ensure_authenticated
from core.browser import browser_session
from core.storage import init_db, upsert_many
from core.utils import logger, ensure_dirs

from scrapers.lms_base import get_semesters, get_courses, fetch_page
from scrapers.lms_assignments import scrape_lms_assignments
from scrapers.lms_quizzes import scrape_lms_quizzes
from scrapers.lms_lecture_notes import scrape_lms_lecture_notes
from scrapers.lms_announcements import scrape_lms_announcements
from scrapers.lms_papers import scrape_lms_papers
from scrapers.lms_course_outline import scrape_lms_course_outline


TARGET_SEMESTER_LABEL = "Fall-2026"

PAGES = [
    ("lms_assignments",  "Assignments.php",  scrape_lms_assignments),
    ("lms_quizzes",      "Quizzes.php",      scrape_lms_quizzes),
    ("lms_lecture_notes", "LectureNotes.php", scrape_lms_lecture_notes),
    ("lms_announcements", "Announcements.php", scrape_lms_announcements),
    ("lms_papers",       "Papers.php",       scrape_lms_papers),
]


def _enter_lms(page) -> bool:
    """Bridge CMS → LMS session by visiting GoToLMS.aspx."""
    try:
        logger.info("Bridging CMS → LMS session via GoToLMS.aspx")
        page.goto("https://cms.bahria.edu.pk/Sys/Common/GoToLMS.aspx",
                  wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(5000)
        # Wait until we're on the LMS domain
        for _ in range(10):
            if "lms.bahria.edu.pk" in page.url:
                logger.info(f"LMS session active: {page.url}")
                return True
            page.wait_for_timeout(1000)
        logger.warning(f"Still not on LMS after bridge: {page.url}")
        return False
    except Exception as e:
        logger.error(f"LMS bridge failed: {e}")
        return False


def scrape_lms_all() -> dict[str, dict]:
    ensure_dirs()
    init_db()
    summary: dict[str, dict] = {}

    with browser_session(use_auth=True, headless=True) as page:
        ensure_authenticated(page)

        if not _enter_lms(page):
            logger.error("Cannot reach LMS — aborting")
            return summary

        # 1. Discover semesters + courses
        sems = get_semesters(page, "Assignments.php")
        logger.info(f"Found {len(sems)} semesters")
        target_sem = next(
            (s for s in sems if TARGET_SEMESTER_LABEL in s["label"]),
            sems[0] if sems else None,
        )
        if not target_sem:
            logger.error("No semesters found")
            return summary
        logger.info(f"Semester: {target_sem['label']} (id={target_sem['id']})")

        courses = get_courses(page, "Assignments.php", target_sem["value"])
        logger.info(f"Found {len(courses)} courses: {[c['label'] for c in courses[:3]]}...")

        # 2. For each page × each course, scrape
        for kind, page_path, parser in PAGES:
            all_items = []
            for c in courses:
                try:
                    html = fetch_page(page, page_path, target_sem["value"], c["value"])
                    items = parser(html, c["label"])
                    all_items.extend(items)
                except Exception as e:
                    logger.error(f"[{kind}] {c['label']}: {e}")

            new, chg = upsert_many(kind, all_items)
            summary[kind] = {"total": len(all_items), "new": new, "changed": chg}
            logger.info(f"[{kind}] {len(all_items)} items ({new} new, {chg} changed)")

        # 3. Course outlines (page-level, no course filter)
        try:
            page.goto("https://lms.bahria.edu.pk/Student/CourseOutline.php",
                      wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(1500)
            outlines = scrape_lms_course_outline(page.content())
            new, chg = upsert_many("lms_course_outlines", outlines)
            summary["lms_course_outlines"] = {"total": len(outlines), "new": new, "changed": chg}
            logger.info(f"[lms_course_outlines] {len(outlines)} items ({new} new, {chg} changed)")
        except Exception as e:
            logger.error(f"[lms_course_outlines] {e}")

    return summary
