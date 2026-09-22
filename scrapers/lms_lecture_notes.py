"""Parse LMS LectureNotes.php HTML."""
from scrapers.lms_base import soup_of, cells, find_main_table
from models.lms import LmsLectureNote


def scrape_lms_lecture_notes(html: str, course: str) -> list[LmsLectureNote]:
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

        # Look for the download link in the "Lecture File(s)" cell
        # (3rd column, index 2). Find the <a> inside it.
        cells_html = r.find_all(["th", "td"])
        files_url = ""
        if len(cells_html) > 2:
            link = cells_html[2].find("a")
            if link and link.get("href"):
                files_url = link["href"]

        out.append(LmsLectureNote(
            course=course,
            week=c[0],
            title=c[1],
            files=c[2] if len(c) > 2 else "",
            files_url=files_url,
            videos=c[3] if len(c) > 3 else "",
            remarks=c[5] if len(c) > 5 else "",
        ))
    return out
