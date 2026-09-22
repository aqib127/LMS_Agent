"""
Daily deadline reminder — emails upcoming (next 48h) + overdue assignments.
Runs at 8 AM via cron.
"""
from datetime import date, timedelta
import re
from core.storage import query, init_db
from core.notifier import send_email
from core.utils import logger, ensure_dirs
from config.settings import settings


MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
}


def parse_date(s: str):
    """Extract the first date from a deadline string."""
    if not s:
        return None
    m = re.search(r"(\d{1,2})\s+(\w+)\s+(\d{4})", s)
    if not m:
        return None
    d, mon_name, y = m.groups()
    mon = MONTHS.get(mon_name.lower())
    if not mon:
        return None
    try:
        return date(int(y), mon, int(d))
    except Exception:
        return None


def main():
    ensure_dirs()
    init_db()

    today = date.today()
    soon = today + timedelta(days=2)

    rows = query("lms_assignments")
    if not rows:
        logger.info("No assignments to remind about")
        return

    upcoming = []
    overdue = []

    for r in rows:
        d = parse_date(r.get("deadline", ""))
        if not d:
            continue
        status = r.get("status", "").lower()
        if "exceeded" in status or d < today:
            overdue.append((d, r))
        elif today <= d <= soon:
            upcoming.append((d, r))

    if not upcoming and not overdue:
        logger.info("Nothing urgent — no reminder sent")
        return

    upcoming.sort(key=lambda t: t[0])
    overdue.sort(key=lambda t: t[0], reverse=True)

    lines = [f"LMS deadline reminder — {today.strftime('%A, %d %B %Y')}"]
    lines.append("=" * 60)
    lines.append("")

    if upcoming:
        lines.append(f"⏰ DUE IN NEXT 48 HOURS ({len(upcoming)}):")
        for d, r in upcoming:
            delta = (d - today).days
            when = "TODAY" if delta == 0 else ("TOMORROW" if delta == 1 else f"in {delta} days")
            lines.append(f"  📅 [{r['course']}] {r['title']} — {when} ({r['deadline']})")
        lines.append(f"\n  → Submit: {settings.lms_base}/Assignments.php")
        lines.append("")

    if overdue:
        lines.append(f"⏰ OVERDUE ({len(overdue)}):")
        for d, r in overdue[:10]:
            lines.append(f"  🔴 [{r['course']}] {r['title']} — was due {d.isoformat()}")
        if len(overdue) > 10:
            lines.append(f"  ... and {len(overdue) - 10} more")
        lines.append(f"\n  → Review: {settings.lms_base}/Assignments.php")

    body = "\n".join(lines)
    subject = f"⏰ {len(upcoming)} due soon · {len(overdue)} overdue — LMS reminder"
    send_email(subject=subject, body=body)
    logger.info(f"Deadline reminder sent: {len(upcoming)} upcoming, {len(overdue)} overdue")


if __name__ == "__main__":
    main()
