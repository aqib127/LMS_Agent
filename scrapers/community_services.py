"""
Parse community_services.html → list[CommunityService].

Table: BodyPH_gvCommunityServices
Columns: Semester, Organization, Job Title, Completed Date, Hours
"""
from scrapers.base import soup_of, cells, find_table_by_id, find_table_by_headers
from models import CommunityService


TABLE_ID = "BodyPH_gvCommunityServices"
REQUIRED = ["Semester", "Organization", "Hours"]


def scrape_community_services(html: str) -> list[CommunityService]:
    soup = soup_of(html)
    t = find_table_by_id(soup, TABLE_ID) or find_table_by_headers(soup, REQUIRED)
    if not t:
        return []
    out: list[CommunityService] = []
    for r in t.find_all("tr")[1:]:
        c = cells(r)
        if len(c) < 5 or not any(c):
            continue
        out.append(CommunityService(
            semester=c[0],
            organization=c[1],
            job_title=c[2],
            completed_date=c[3],
            hours=c[4],
        ))
    return out
