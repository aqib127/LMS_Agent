"""Parse LMS Announcements.php HTML."""
from scrapers.lms_base import soup_of, cells, find_main_table
from models.lms import LmsAnnouncement


def scrape_lms_announcements(html: str, course: str) -> list[LmsAnnouncement]:
    soup = soup_of(html)
    t = find_main_table(soup)
    if not t:
        return []
    rows = t.find_all("tr")
    out = []
    for r in rows[1:]:
        c = cells(r)
        if len(c) < 3 or not c[0].strip():
            continue
        out.append(LmsAnnouncement(
            course=course,
            number=c[0],
            title=c[1],
            body=c[2],
            posted_date=c[3] if len(c) > 3 else "",
        ))
    return out
