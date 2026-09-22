"""
Command dispatcher for the LMS chatbot.
Handles /commands and free-form questions.

NOTE: scraper imports are LAZY (inside functions) so this module can be
imported on hosts without Playwright installed (e.g. Wispbyte 512MB).
"""
import re
from datetime import datetime
from core.ai_engine import (
    answer as llm_answer,
    lowest_attendance, unpaid_fees, upcoming_exams, recent_results,
)
from core.storage import query, stats
from core.utils import logger


HELP_TEXT = """*LMS Agent — commands*

*CMS:*
• `/attendance` — attendance per course
• `/lowest` — courses with lowest attendance
• `/fees` — all fee challans
• `/unpaid` — only unpaid fees
• `/results` — recent exam results
• `/exams` — scheduled exams
• `/courses` — registered courses
• `/gpa` — computed GPA

*LMS:*
• `/assignments` — all assignments
• `/deadlines` — upcoming + overdue (sorted)
• `/due` — what's due in next 7 days
• `/quizzes` — quizzes per course
• `/announcements` — latest announcements
• `/notes <course>` — lecture notes for a course
• `/download list` — lecture notes that can be downloaded
• `/download <course> <week>` — download a specific lecture
• `/download url <rel_url>` — download by raw URL
• `/papers` — past papers

*Actions:*
• `/refresh` — refresh CMS data (~15 sec)
• `/refresh-lms` — deep refresh LMS (~3 min)
• `/stats` — how many rows stored
• `/help` — this message

*Or ask a question:*
  "What's due this week?"
  "Show me Operating Systems lecture notes"
  "Any new announcements?"
"""


# ---------- Course matching helper ----------

def _course_matches(term: str, course_name: str) -> bool:
    """Match if term is substring OR matches initials of course words."""
    term = term.lower().strip()
    cn = course_name.lower()
    if term in cn:
        return True
    words = [w for w in re.split(r"\W+", cn) if w]
    initials = "".join(w[0] for w in words)
    if term == initials:
        return True
    if len(term) >= 2 and term in initials:
        return True
    return False


# ---------- CMS handlers ----------

def cmd_attendance() -> str:
    rows = query("attendance")
    if not rows:
        return "No attendance records. Try `/refresh` first."
    lines = ["*Attendance:*"]
    for r in sorted(rows, key=lambda x: x["code"]):
        warn = " ⚠️" if r["percentage"] < 75 else ""
        lines.append(f"• {r['code']} — {r['title']}: {r['percentage']}%{warn}")
    return "\n".join(lines)


def cmd_lowest() -> str:
    return lowest_attendance(n=5)


def cmd_fees() -> str:
    rows = query("fees")
    if not rows:
        return "No fee challans. Try `/refresh` first."
    lines = ["*Fees:*"]
    for r in rows:
        emoji = "✅" if r["status"] == "Paid" else "⚠️"
        lines.append(
            f"{emoji} {r['semester']} — {r['amount']} — {r['status']} "
            f"(due {r['due_date']})"
        )
    return "\n".join(lines)


def cmd_unpaid() -> str:
    return unpaid_fees()


def cmd_results() -> str:
    return recent_results()


def cmd_exams() -> str:
    return upcoming_exams()


def cmd_courses() -> str:
    rows = query("courses")
    if not rows:
        return "No courses. Try `/refresh` first."
    lines = ["*Registered courses:*"]
    for r in rows:
        lines.append(
            f"• {r['code']} — {r['title']} ({r['credit_hours']} CH) — {r['teacher']}"
        )
    return "\n".join(lines)


def cmd_gpa() -> str:
    rows = query("exam_results")
    graded = [r for r in rows if r.get("grade") and r["grade"] != "N/A"]
    if not graded:
        return "No graded courses yet."
    total_ch = sum(r["credit_hours"] for r in graded)
    total_pts = sum(r["product"] for r in graded)
    gpa = round(total_pts / total_ch, 2) if total_ch else 0.0
    lines = [f"*Semester GPA: {gpa}* (over {total_ch} credit hours)"]
    lines.append("")
    lines.append("*Graded courses:*")
    for r in sorted(graded, key=lambda x: x["code"]):
        lines.append(
            f"• {r['code']} — {r['title']}: {r['grade']} "
            f"({r['grade_points']} × {r['credit_hours']} CH)"
        )
    return "\n".join(lines)


# ---------- LMS handlers ----------

def cmd_assignments() -> str:
    rows = query("lms_assignments")
    if not rows:
        return "No assignments. Try `/refresh-lms` first."
    lines = [f"*Assignments ({len(rows)}):*"]
    for r in rows:
        lines.append(f"• [{r['course']}] #{r['number']} {r['title']} — due {r['deadline']}")
    return "\n".join(lines)


def cmd_deadlines() -> str:
    rows = query("lms_assignments")
    if not rows:
        return "No assignments. Try `/refresh-lms` first."

    def is_overdue(r):
        return "exceeded" in r.get("status", "").lower()

    upcoming = sorted([r for r in rows if not is_overdue(r)],
                      key=lambda r: r.get("deadline", ""))
    overdue = sorted([r for r in rows if is_overdue(r)],
                     key=lambda r: r.get("deadline", ""), reverse=True)

    lines = []
    if upcoming:
        lines.append(f"*Upcoming ({len(upcoming)}):*")
        for r in upcoming:
            lines.append(f"📅 [{r['course']}] {r['title']} — {r['deadline']}")
    if overdue:
        if lines:
            lines.append("")
        lines.append(f"*Overdue ({len(overdue)}):*")
        for r in overdue[:10]:
            lines.append(f"⏰ [{r['course']}] {r['title']} — {r['deadline']}")
        if len(overdue) > 10:
            lines.append(f"... and {len(overdue) - 10} more.")
    return "\n".join(lines)


def cmd_due() -> str:
    from datetime import date, timedelta
    rows = query("lms_assignments")
    if not rows:
        return "No assignments. Try `/refresh-lms` first."

    today = date.today()
    end = today + timedelta(days=7)
    months = {
        "january": 1, "february": 2, "march": 3, "april": 4,
        "may": 5, "june": 6, "july": 7, "august": 8,
        "september": 9, "october": 10, "november": 11, "december": 12,
    }

    def parse(s):
        m = re.search(r"(\d{1,2})\s+(\w+)\s+(\d{4})", s or "")
        if not m:
            return None
        d, mon_name, y = m.groups()
        mon = months.get(mon_name.lower())
        if not mon:
            return None
        try:
            return date(int(y), mon, int(d))
        except Exception:
            return None

    found = []
    for r in rows:
        d = parse(r.get("deadline", ""))
        if d and today <= d <= end:
            found.append((d, r))
    found.sort(key=lambda t: t[0])

    lines = [f"*Due in next 7 days (from {today.isoformat()}):*"]
    if not found:
        lines.append("• Nothing due in the next 7 days. ✅")
    else:
        for d, r in found:
            lines.append(f"📅 {d.isoformat()} — [{r['course']}] {r['title']}")
    return "\n".join(lines)


def cmd_quizzes() -> str:
    rows = query("lms_quizzes")
    if not rows:
        return "No quizzes posted yet this semester."
    lines = [f"*Quizzes ({len(rows)}):*"]
    for r in rows:
        lines.append(f"• [{r['course']}] #{r['number']} {r['title']} — marks {r['marks']}")
    return "\n".join(lines)


def cmd_announcements() -> str:
    rows = query("lms_announcements")
    if not rows:
        return "No announcements. Try `/refresh-lms` first."
    lines = [f"*Announcements ({len(rows)}):*"]
    for r in rows:
        body = r.get("body", "")
        preview = body[:140] + "..." if len(body) > 140 else body
        lines.append(f"📢 [{r['course']}] {r['title']} ({r['posted_date']})")
        if preview:
            lines.append(f"   {preview}")
    return "\n".join(lines)


def cmd_notes(args: list[str]) -> str:
    rows = query("lms_lecture_notes")
    if not rows:
        return "No lecture notes. Try `/refresh-lms` first."
    if args:
        term = " ".join(args).lower()
        rows = [r for r in rows if _course_matches(term, r["course"])]
        if not rows:
            return f"No notes found matching '{term}'."
    from collections import defaultdict
    by_course = defaultdict(list)
    for r in rows:
        by_course[r["course"]].append(r)
    lines = []
    for course, items in by_course.items():
        lines.append(f"*{course}* ({len(items)} notes):")
        for r in items[:20]:
            tags = []
            if r.get("files_url"):
                tags.append("📥")
            elif r.get("files"):
                tags.append("📄")
            if r.get("videos"):
                tags.append("🎥")
            tag_str = " ".join(tags)
            lines.append(f"  Wk {r['week']:>3}: {r['title']} {tag_str}")
        if len(items) > 20:
            lines.append(f"  ... and {len(items) - 20} more")
        lines.append("")
    return "\n".join(lines).strip()


def cmd_download(args: list[str]) -> str:
    """
    /download list
    /download <course> <week>
    /download url <relative_url>
    """
    try:
        from core.downloader import download_file
    except ImportError as e:
        return f"❌ Downloads not available on this host (missing playwright). {e}"

    if not args:
        return (
            "*Usage:*\n"
            "• `/download list` — see available lecture notes\n"
            "• `/download <course> <week>` — download by course + week\n"
            "• `/download url <rel_url>` — download by raw URL"
        )

    if args[0].lower() == "list":
        rows = query("lms_lecture_notes")
        with_urls = [r for r in rows if r.get("files_url")]
        if not with_urls:
            return "No downloadable lecture notes found. Try `/refresh-lms` first."
        lines = [f"*Downloadable lectures ({len(with_urls)}):*"]
        for r in with_urls[:40]:
            lines.append(f"• `{r['course']}` Wk {r['week']}: {r['title']}")
        if len(with_urls) > 40:
            lines.append(f"... and {len(with_urls) - 40} more.")
        lines.append("")
        lines.append("Use: `/download <course> <week>`")
        return "\n".join(lines)

    if args[0].lower() == "url":
        if len(args) < 2:
            return "Usage: `/download url <relative_path>`"
        url = " ".join(args[1:])
        try:
            p = download_file(url, course="misc", name="file")
            return f"✅ Downloaded: `{p.name}` ({p.stat().st_size // 1024} KB)"
        except Exception as e:
            logger.exception("download by url failed")
            return f"❌ Download failed: {e}"

    if len(args) < 2:
        return "Usage: `/download <course> <week>`\nExample: `/download operating 5`"

    course_term = " ".join(args[:-1]).lower()
    week = str(args[-1]).strip()

    rows = query("lms_lecture_notes")
    matches = [
        r for r in rows
        if _course_matches(course_term, r["course"])
        and str(r.get("week", "")).strip() == week
        and r.get("files_url")
    ]
    if not matches:
        return (
            f"❌ No lecture found for course='{course_term}' week={week}.\n"
            "Try `/download list`."
        )

    if len(matches) > 1:
        courses = sorted(set(m["course"] for m in matches))
        lines = [f"⚠️ Multiple courses match '{course_term}' at week {week}:"]
        for c in courses:
            lines.append(f"• {c}")
        lines.append("")
        lines.append("Be more specific. Example: `/download artificial intelligence 4`")
        return "\n".join(lines)

    r = matches[0]
    try:
        p = download_file(
            rel_url=r["files_url"],
            course=r["course"],
            name=f"Wk{week}-{r['title']}",
        )
        return (
            f"✅ *Downloaded*\n"
            f"• Course: {r['course']}\n"
            f"• Week: {week} — {r['title']}\n"
            f"• File: `{p.name}` ({p.stat().st_size // 1024} KB)\n"
            f"• Location: `{p}`"
        )
    except Exception as e:
        logger.exception("download failed")
        return f"❌ Download failed: {e}"


def cmd_papers() -> str:
    rows = query("lms_papers")
    if not rows:
        return "No past papers posted."
    lines = [f"*Past papers ({len(rows)}):*"]
    for r in rows:
        tag = " 📥" if r.get("paper_url") else ""
        lines.append(f"• [{r['course']}] {r['term']} — {r['paper']}{tag}")
    return "\n".join(lines)


# ---------- Actions ----------

def cmd_stats() -> str:
    s = stats()
    if not s:
        return "Database is empty. Run `/refresh` first."
    lines = ["*DB totals:*"]
    for kind, n in sorted(s.items()):
        lines.append(f"• {kind}: {n}")
    return "\n".join(lines)


def cmd_refresh() -> str:
    """Refresh CMS. Lazy-imports scrapers to avoid needing playwright at startup."""
    try:
        from core.scraper_runner import scrape_all_live
    except ImportError as e:
        return (
            "❌ Scrapers not available on this host "
            f"(missing playwright): {e}"
        )
    try:
        summary = scrape_all_live()
        lines = ["*CMS refreshed.*"]
        for kind, s in summary.items():
            if "error" in s:
                lines.append(f"⚠️ {kind}: {s['error']}")
            else:
                lines.append(
                    f"• {kind}: {s['total']} items "
                    f"({s['new']} new, {s['changed']} changed)"
                )
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"refresh failed: {e}")
        return f"❌ Refresh failed: {e}"


def cmd_refresh_lms() -> str:
    """Refresh LMS. Lazy-imports scrapers to avoid needing playwright at startup."""
    try:
        from core.lms_runner import scrape_lms_all
    except ImportError as e:
        return (
            "❌ LMS scrapers not available on this host "
            f"(missing playwright): {e}"
        )
    try:
        summary = scrape_lms_all()
        lines = ["*LMS deep refresh done.*"]
        for kind, s in summary.items():
            lines.append(
                f"• {kind}: {s['total']} items "
                f"({s['new']} new, {s['changed']} changed)"
            )
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"lms refresh failed: {e}")
        return f"❌ LMS refresh failed: {e}"


def cmd_help() -> str:
    return HELP_TEXT


# ---------- Router ----------

COMMANDS = {
    "/attendance":    cmd_attendance,
    "/att":           cmd_attendance,
    "/lowest":        cmd_lowest,
    "/fees":          cmd_fees,
    "/unpaid":        cmd_unpaid,
    "/results":       cmd_results,
    "/exams":         cmd_exams,
    "/courses":       cmd_courses,
    "/gpa":           cmd_gpa,
    "/assignments":   cmd_assignments,
    "/deadlines":     cmd_deadlines,
    "/due":           cmd_due,
    "/quizzes":       cmd_quizzes,
    "/announcements": cmd_announcements,
    "/announce":      cmd_announcements,
    "/notes":         cmd_notes,
    "/download":      cmd_download,
    "/papers":        cmd_papers,
    "/stats":         cmd_stats,
    "/refresh":       cmd_refresh,
    "/refresh-lms":   cmd_refresh_lms,
    "/help":          cmd_help,
    "/start":         cmd_help,
}

ARG_COMMANDS = {"/notes", "/download"}


def handle(text: str) -> str:
    text = (text or "").strip()
    if not text:
        return "Send /help to see what I can do."

    parts = text.split()
    first = parts[0].lower()
    args = parts[1:]

    if first in COMMANDS:
        try:
            if first in ARG_COMMANDS:
                return COMMANDS[first](args)
            return COMMANDS[first]()
        except Exception as e:
            logger.exception("command failed")
            return f"❌ Command failed: {e}"

    # Deterministic shortcuts — don't trust the LLM for these
    lower = text.lower()
    if "lowest attendance" in lower or "worst attendance" in lower \
       or "attendance lowest" in lower or "least attendance" in lower:
        return lowest_attendance(n=5)

    if "unpaid fee" in lower or "fee due" in lower or "pending fee" in lower:
        return unpaid_fees()

    if "next exam" in lower or "upcoming exam" in lower:
        return upcoming_exams()

    try:
        return llm_answer(text)
    except Exception as e:
        logger.exception("LLM answer failed")
        return f"❌ Sorry, I couldn't answer that: {e}"
