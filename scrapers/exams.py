"""
Parse exam_result.html → list[ExamResult].

Student info is in table[0]. Results are in the remaining 3+ tables
with headers: #, Code, Title, Majors, Credit Hours, Grade, Grade Points, Product
"""
from scrapers.base import soup_of, cells, all_data_tables, to_float
from models import ExamResult


REQUIRED = ["Code", "Title", "Credit Hours", "Grade Points"]


def scrape_exam_results(html: str, semester: str = "") -> list[ExamResult]:
    soup = soup_of(html)
    # Grab the semester label from the student info table if possible
    info_t = soup.find("table", class_="tableCol4")
    if info_t and not semester:
        for r in info_t.find_all("tr"):
            c = cells(r)
            for i, cell in enumerate(c):
                if cell.strip().lower() == "intake semester" and i + 1 < len(c):
                    semester = c[i + 1]
                    break

    tables = all_data_tables(soup, REQUIRED)
    out: list[ExamResult] = []
    for t in tables:
        for r in t.find_all("tr")[1:]:
            c = cells(r)
            if len(c) < 8:
                continue
            gp = c[6]
            prod = c[7]
            out.append(ExamResult(
                code=c[1],
                title=c[2],
                credit_hours=int(to_float(c[4])),
                grade=c[5],
                grade_points=to_float(gp),
                product=to_float(prod),
                semester=semester,
            ))
    return out
