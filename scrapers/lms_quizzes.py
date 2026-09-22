"""Parse LMS Quizzes.php HTML."""
from scrapers.lms_base import soup_of, cells, find_main_table
from models.lms import LmsQuiz


def scrape_lms_quizzes(html: str, course: str) -> list[LmsQuiz]:
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
        out.append(LmsQuiz(
            course=course,
            number=c[0],
            title=c[1],
            marks=c[3] if len(c) > 3 else "",
            solution=c[4] if len(c) > 4 else "",
        ))
    return out
