"""
Parse registered_courses.html → list[Course].

Columns: #, Code, Registered Course Title, Credit Hours, Majors,
         Offered Course Title, Class, Teacher Name, Teacher Email,
         Fee Status, Actions
"""
from scrapers.base import soup_of, cells, all_data_tables, to_float
from models import Course


REQUIRED = ["Code", "Registered Course Title", "Teacher Email"]


def scrape_courses(html: str) -> list[Course]:
    soup = soup_of(html)
    tables = all_data_tables(soup, REQUIRED)
    out: list[Course] = []
    for t in tables:
        for r in t.find_all("tr")[1:]:
            c = cells(r)
            if len(c) < 10:
                continue
            out.append(Course(
                code=c[1],
                title=c[2],
                credit_hours=int(to_float(c[3])),
                offered_title=c[5],
                class_name=c[6],
                teacher=c[7],
                teacher_email=c[8],
                fee_status=c[9],
            ))
    return out
