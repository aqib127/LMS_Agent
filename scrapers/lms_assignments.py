"""Parse LMS Assignments.php HTML."""
import re
from scrapers.lms_base import soup_of, cells, find_main_table
from models.lms import LmsAssignment


DEADLINE_DATE_RE = re.compile(r"\d{1,2}\s+\w+\s+\d{4}[^,]*?am|pm", re.IGNORECASE)


def _clean_deadline(s: str) -> str:
    """Remove 'Delete'/'Submit'/'Deadline Exceeded' labels that got scraped in."""
    # Cut off at any obvious button label
    for cut in (" Delete", " Submit", " Deadline Exceeded", " Assignment"):
        idx = s.find(cut)
        if idx > 0:
            s = s[:idx]
    return s.strip()


def _clean_status(s: str) -> str:
    """Status may contain 'Deadline Exceeded', 'Submit', 'Delete', etc."""
    s = s.strip()
    if "exceeded" in s.lower():
        return "Deadline Exceeded"
    if "submit" in s.lower():
        return "Submit"
    if "delete" in s.lower():
        return "Delete"
    if "pending" in s.lower():
        return "Pending"
    return s


def scrape_lms_assignments(html: str, course: str) -> list[LmsAssignment]:
    soup = soup_of(html)
    t = find_main_table(soup)
    if not t:
        return []
    rows = t.find_all("tr")
    if len(rows) < 2:
        return []
    out = []
    for r in rows[1:]:
        c = cells(r)
        if len(c) < 4 or not c[0].strip():
            continue
        # Columns: #, Title, Assignment, AddedSubmission, Marks, Returned, Action, Deadline
        deadline = _clean_deadline(c[7] if len(c) > 7 else "")
        # status is the "Action" column, but it can be blank if the assignment is not yet graded.
        # Better: derive from Action text (Submit / Delete / Deadline Exceeded)
        raw_action = c[6] if len(c) > 6 else ""
        status = _clean_status(raw_action) if raw_action else "Pending"

        out.append(LmsAssignment(
            course=course,
            number=c[0],
            title=c[1],
            added=c[3] if len(c) > 3 else "",
            marks_obtained=c[4] if len(c) > 4 else "",
            status=status,
            deadline=deadline,
        ))
    return out
