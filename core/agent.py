"""
End-to-end agent run: refresh CMS → diff → email if anything changed.
LMS deep refresh is handled separately by core/lms_runner.
"""
from core.scraper_runner import scrape_all_live
from core.storage import init_db, query
from core.ai_engine import digest
from core.notifier import send_email, send_discord
from core.utils import logger, ensure_dirs


def _build_subject(events: dict, n_new: int, n_changed: int) -> str:
    """Descriptive subject line with category emojis."""
    parts = []
    if events.get("exam_results"):
        graded = [i for i in events["exam_results"]
                  if i.get("grade") and i["grade"] != "N/A"]
        if graded:
            parts.append(f"🎓 {len(graded)} new grade(s)")
    if events.get("lms_assignments"):
        new_a = [i for i in events["lms_assignments"]
                 if "exceeded" not in i.get("status", "").lower()]
        over_a = [i for i in events["lms_assignments"]
                  if "exceeded" in i.get("status", "").lower()]
        if new_a:
            parts.append(f"📚 {len(new_a)} assignment(s)")
        if over_a:
            parts.append(f"⏰ {len(over_a)} overdue")
    if events.get("lms_announcements"):
        parts.append(f"📢 {len(events['lms_announcements'])} announcement(s)")
    if events.get("lms_lecture_notes"):
        parts.append(f"📄 {len(events['lms_lecture_notes'])} note(s)")
    if events.get("lms_quizzes"):
        parts.append(f"📝 {len(events['lms_quizzes'])} quiz(zes)")
    if events.get("fees"):
        unpaid = [i for i in events["fees"]
                  if i.get("status", "").lower() != "paid"]
        if unpaid:
            parts.append(f"💰 {len(unpaid)} fee(s) due")
    if events.get("attendance"):
        low = [i for i in events["attendance"]
               if i.get("percentage", 100) < 75]
        if low:
            parts.append(f"📉 {len(low)} low attendance")

    if not parts:
        return f"LMS update — {n_new} new, {n_changed} changed"

    return "LMS: " + " · ".join(parts[:4])


def run_once(notify: bool = True) -> dict:
    """One full CMS cycle. Returns summary dict."""
    ensure_dirs()
    init_db()

    logger.info("Agent run starting")
    summary = scrape_all_live()

    events: dict[str, list[dict]] = {}
    total_new = 0
    total_changed = 0

    for kind, s in summary.items():
        if "error" in s:
            logger.error(f"[{kind}] scrape error: {s['error']}")
            continue
        n_new = s.get("new", 0)
        n_chg = s.get("changed", 0)
        total_new += n_new
        total_changed += n_chg

        if n_new or n_chg:
            latest = query(kind)
            events[kind] = latest[-max(n_new + n_chg, 1):]

    logger.info(f"Agent run done: {total_new} new, {total_changed} changed")

    if notify and (total_new or total_changed):
        body = digest(events)
        if body:
            subject = _build_subject(events, total_new, total_changed)
            send_email(subject=subject, body=body)
            send_discord(f"**{subject}**\n\n{body}")
            logger.info(f"Notification sent (email + Discord): {subject}")
    elif notify:
        logger.info("No changes, skipping email")

    return {"new": total_new, "changed": total_changed, "summary": summary}


def run_lms_and_notify() -> dict:
    """Deep LMS refresh with email digest."""
    from core.lms_runner import scrape_lms_all

    ensure_dirs()
    init_db()
    logger.info("LMS deep refresh starting")
    summary = scrape_lms_all()

    events: dict[str, list[dict]] = {}
    total_new = 0
    total_changed = 0

    for kind, s in summary.items():
        n_new = s.get("new", 0)
        n_chg = s.get("changed", 0)
        total_new += n_new
        total_changed += n_chg
        if n_new or n_chg:
            latest = query(kind)
            events[kind] = latest[-max(n_new + n_chg, 1):]

    logger.info(f"LMS deep refresh done: {total_new} new, {total_changed} changed")

    if total_new or total_changed:
        body = digest(events)
        if body:
            subject = _build_subject(events, total_new, total_changed)
            send_email(subject=subject, body=body)
            logger.info(f"LMS notification email sent: {subject}")

    return {"new": total_new, "changed": total_changed, "summary": summary}
