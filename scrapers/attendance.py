"""
Parse attendance.html → list[AttendanceRecord].

Columns: #, Code, Registered Course Title, Credit Hours, Majors,
         Offered Course Title, Class, Teacher Name, Fee Status,
         Present Hours, Absent Hours, Total Hours, Actions

Present Hours column is "6.0 :66.67%" (hours : percentage).
"""
import re
from scrapers.base import soup_of, cells, all_data_tables, to_float
from models import AttendanceRecord


REQUIRED = ["Code", "Registered Course Title", "Present Hours"]


def _parse_present(cell: str) -> tuple[float, float]:
    """Return (hours, percentage) from '6.0 :66.67%'."""
    m = re.match(r"([\d.]+)\s*:\s*([\d.]+)%", cell)
    if m:
        return float(m.group(1)), float(m.group(2))
    # sometimes just "6.0"
    try:
        return float(cell), 0.0
    except Exception:
        return 0.0, 0.0


def scrape_attendance(html: str) -> list[AttendanceRecord]:
    soup = soup_of(html)
    tables = all_data_tables(soup, REQUIRED)
    out: list[AttendanceRecord] = []
    for t in tables:
        for r in t.find_all("tr")[1:]:  # skip header
            c = cells(r)
            if len(c) < 12:
                continue
            present_hours, percentage = _parse_present(c[9])
            out.append(AttendanceRecord(
                code=c[1],
                title=c[2],
                credit_hours=int(to_float(c[3])),
                class_name=c[6],
                teacher=c[7],
                present_hours=present_hours,
                absent_hours=to_float(c[10]),
                total_hours=to_float(c[11]),
                percentage=percentage,
            ))
    return out
