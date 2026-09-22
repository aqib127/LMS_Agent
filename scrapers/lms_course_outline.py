"""Parse LMS CourseOutline.php HTML."""
from scrapers.lms_base import soup_of, cells, find_main_table
from models.lms import LmsCourseOutline


def scrape_lms_course_outline(html: str, course: str = "") -> list[LmsCourseOutline]:
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
        # Columns: #, Course, "Download Course Outline" (link)
        link_el = r.find("a")
        url = link_el.get("href", "") if link_el else ""
        out.append(LmsCourseOutline(course=c[1], outline_url=url))
    return out
