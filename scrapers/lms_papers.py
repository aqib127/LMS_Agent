"""Parse LMS Papers.php HTML."""
from scrapers.lms_base import soup_of, cells, find_main_table
from models.lms import LmsPaperDownload


def scrape_lms_papers(html: str, course: str) -> list[LmsPaperDownload]:
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
        cells_html = r.find_all(["th", "td"])
        paper_url = ""
        if len(cells_html) > 2:
            link = cells_html[2].find("a")
            if link and link.get("href"):
                paper_url = link["href"]
        out.append(LmsPaperDownload(
            course=course,
            number=c[0],
            term=c[1],
            paper=c[2] if len(c) > 2 else "",
            paper_url=paper_url,
            remarks=c[3] if len(c) > 3 else "",
            marks=c[5] if len(c) > 5 else "",
            deadline=c[9] if len(c) > 9 else "",
        ))
    return out
