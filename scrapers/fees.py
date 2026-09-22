"""
Parse fee_challans.html → list[FeeChallan].

Columns: Semester, Type, Challan No., Amount, Due Date, Status,
         Deposit Date, Remarks, Actions
"""
from scrapers.base import soup_of, cells, all_data_tables
from models import FeeChallan


REQUIRED = ["Semester", "Challan No.", "Amount", "Due Date", "Status"]


def scrape_fee_challans(html: str) -> list[FeeChallan]:
    soup = soup_of(html)
    tables = all_data_tables(soup, REQUIRED)
    out: list[FeeChallan] = []
    for t in tables:
        for r in t.find_all("tr")[1:]:
            c = cells(r)
            if len(c) < 7:
                continue
            out.append(FeeChallan(
                semester=c[0],
                type=c[1],
                challan_no=c[2],
                amount=c[3],
                due_date=c[4],
                status=c[5],
                deposit_date=c[6],
                remarks=c[7] if len(c) > 7 else "",
            ))
    return out
