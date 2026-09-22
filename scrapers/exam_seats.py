"""
Parse exam_seats.html → list[ExamSeat].

Table: BodyPH_studentExamSeats_gvExamSeats
Columns: #, Title, Class, Date, Session, Start Time, Room, Row,
         Column, Status, Fee Defaulter, Surveys
"""
from scrapers.base import soup_of, cells, find_table_by_id, find_table_by_headers
from models import ExamSeat


TABLE_ID = "BodyPH_studentExamSeats_gvExamSeats"
REQUIRED = ["Title", "Class", "Date", "Room"]


def scrape_exam_seats(html: str) -> list[ExamSeat]:
    soup = soup_of(html)
    t = find_table_by_id(soup, TABLE_ID) or find_table_by_headers(soup, REQUIRED)
    if not t:
        return []
    out: list[ExamSeat] = []
    for r in t.find_all("tr")[1:]:
        c = cells(r)
        if len(c) < 8:
            continue
        out.append(ExamSeat(
            title=c[1],
            class_name=c[2],
            date=c[3],
            session=c[4],
            start_time=c[5],
            room=c[6],
            row=c[7],
            column=c[8] if len(c) > 8 else "",
            status=c[9] if len(c) > 9 else "",
            fee_defaulter=c[10] if len(c) > 10 else "",
        ))
    return out
