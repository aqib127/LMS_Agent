"""Parse LMS CoursePlan.php HTML."""
from scrapers.lms_base import soup_of, cells, find_main_table
from models.lms import LmsCoursePlan


def scrape_lms_course_plan(html: str, course: str) -> list[LmsCoursePlan]:
    soup = soup_of(html)
    t = find_main_table(soup)
    if not t:
        return []
    rows = t.find_all("tr")
    out = []
    for r in rows[1:]:
        c = cells(r)
        if len(c) < 3:
            continue
        if "Please select" in c[0]:
            continue
        out.append(LmsCoursePlan(
            course=course,
            week=c[0],
            content=c[1],
            outcome=c[2] if len(c) > 2 else "",
        ))
    return out
