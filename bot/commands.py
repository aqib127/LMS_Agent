"""
Command dispatcher for the LMS chatbot.
Handles /commands and free-form questions.

NOTE: scraper imports are LAZY (inside functions) so this module can be
imported on hosts without Playwright installed (e.g. Wispbyte 512MB).
"""
import re
from datetime import datetime
from pathlib import Path

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
• `/papers` — past papers

*Files:*
• `/download list` — all downloadable files
• `/download <search>` — search & download any file
• `/download url <rel_url>` — download by raw URL
• `/upload <assignment> <file>` — stage a file for submission
• `/confirm` — submit the staged file (or type: CONFIRM UPLOAD)
• `/cancel` — abort a pending upload

*Natural language:*
• "upload my assignment 1"
• "submit uninformed search"

*Actions:*
• `/refresh` — refresh CMS data (~15 sec)
• `/refresh-lms` — deep refresh LMS (~3 min)
• `/stats` — how many rows stored
• `/help` — this message
"""


# ---------- Helpers ----------

def _course_matches(term: str, course_name: str) -> bool:
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


def _initials_of(text: str) -> str:
    ws = [w for w in re.split(r"\W+", text.lower()) if w]
    return "".join(w[0] for w in ws)


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
        lines.append(
            f"• [{r['course']}] #{r['number']} {r['title']} — due {r['deadline']}"
        )
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
    try:
        from core.downloader import download_file
    except ImportError as e:
        return f"❌ Downloads not available on this host (missing playwright). {e}"

    items = []

    for r in query("lms_lecture_notes"):
        if r.get("files_url"):
            items.append({
                "kind": "notes",
                "course": r["course"],
                "name": f"Wk {r['week']} — {r['title']}",
                "url": r["files_url"],
            })

    for r in query("lms_assignments"):
        url = r.get("solution_url") or r.get("submission_url") or ""
        if url:
            items.append({
                "kind": "assignments",
                "course": r["course"],
                "name": f"#{r['number']} {r['title']}",
                "url": url,
            })

    for r in query("lms_quizzes"):
        if r.get("quiz_url"):
            items.append({
                "kind": "quizzes",
                "course": r["course"],
                "name": f"#{r['number']} {r['title']}",
                "url": r["quiz_url"],
            })

    for r in query("lms_papers"):
        if r.get("paper_url"):
            items.append({
                "kind": "papers",
                "course": r["course"],
                "name": f"{r['term']} — {r['paper']}",
                "url": r["paper_url"],
            })

    for r in query("lms_course_outlines"):
        if r.get("outline_url"):
            items.append({
                "kind": "outlines",
                "course": r["course"],
                "name": "Course outline",
                "url": r["outline_url"],
            })

    if not args:
        return (
            "*Usage:*\n"
            "• `/download list` — all downloadable files\n"
            "• `/download list assignments` — filter by kind\n"
            "• `/download <search terms>` — search and download\n"
            "• `/download url <rel_url>` — download by raw URL\n\n"
            "_Kinds: notes, assignments, quizzes, papers, outlines_"
        )

    if args[0].lower() == "list":
        kind_filter = args[1].lower() if len(args) > 1 else None
        shown = items if not kind_filter else [i for i in items if i["kind"] == kind_filter]
        if not shown:
            return f"No downloadable files found for kind='{kind_filter}'."
        lines = [f"*Downloadable files ({len(shown)}):*"]
        for it in shown[:40]:
            lines.append(f"• `[{it['kind']}]` {it['course']} — {it['name']}")
        if len(shown) > 40:
            lines.append(f"... and {len(shown) - 40} more.")
        lines.append("")
        lines.append("Use: `/download <search terms>`")
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

    query_str = " ".join(args).lower()
    words = [w for w in query_str.split() if w]

    matches = [it for it in items
               if all(w in f"{it['course']} {it['name']} {it['kind']}".lower()
                      for w in words)]

    if not matches:
        matches = [it for it in items
                   if any(w in f"{it['course']} {it['name']} {it['kind']}".lower()
                          for w in words)]

    if matches:
        matches.sort(key=lambda m: {"assignments": 0, "notes": 1, "quizzes": 2,
                                     "papers": 3, "outlines": 4}.get(m["kind"], 9))

    if not matches:
        return f"❌ No downloadable file matches `{query_str}`."

    if len(matches) > 1:
        lines = [f"⚠️ Multiple files match `{query_str}`:"]
        for it in matches[:8]:
            lines.append(f"• `[{it['kind']}]` {it['course']} — {it['name']}")
        if len(matches) > 8:
            lines.append(f"... and {len(matches) - 8} more")
        lines.append("")
        lines.append("Refine your search to pick one.")
        return "\n".join(lines)

    it = matches[0]
    try:
        p = download_file(
            rel_url=it["url"],
            course=it["course"],
            name=it["name"],
        )
        return (
            f"✅ *Downloaded*\n"
            f"• Kind: {it['kind']}\n"
            f"• Course: {it['course']}\n"
            f"• Name: {it['name']}\n"
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
    try:
        from core.scraper_runner import scrape_all_live
    except ImportError as e:
        return f"❌ Scrapers not available on this host (missing playwright): {e}"
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
    try:
        from core.lms_runner import scrape_lms_all
    except ImportError as e:
        return f"❌ LMS scrapers not available on this host (missing playwright): {e}"
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


# ---------- Course ID lookup (for uploads) ----------

_COURSE_B64_CACHE: dict = {}


def _lookup_course_b64(course_name: str) -> str:
    global _COURSE_B64_CACHE
    if not _COURSE_B64_CACHE:
        try:
            from scrapers.lms_base import get_semesters, get_courses
            from core.auth import ensure_authenticated
            from core.browser import browser_session
            with browser_session(use_auth=True, headless=True) as page:
                ensure_authenticated(page)
                page.goto(
                    "https://cms.bahria.edu.pk/Sys/Common/GoToLMS.aspx",
                    wait_until="domcontentloaded", timeout=30000,
                )
                page.wait_for_timeout(5000)
                sems = get_semesters(page, "Assignments.php")
                sem = next(
                    (s for s in sems if "Fall-2026" in s["label"]), sems[0]
                )
                courses = get_courses(page, "Assignments.php", sem["value"])
                for c in courses:
                    _COURSE_B64_CACHE[c["label"].lower()] = c["value"]
        except Exception as e:
            logger.error(f"Failed to fetch course IDs: {e}")
            return ""

    name_lower = course_name.lower()
    if name_lower in _COURSE_B64_CACHE:
        return _COURSE_B64_CACHE[name_lower]
    for k, v in _COURSE_B64_CACHE.items():
        if name_lower in k or k in name_lower:
            return v
    return ""


# ---------- Upload commands ----------

_PENDING_UPLOAD: dict = {}


def _do_upload_staging(
    search: str,
    staged_path: "Path",
) -> str:
    """
    Shared helper for /upload and natural-language upload.
    Finds the assignment, stages the file, returns the confirmation prompt.
    """
    try:
        from core.uploader import prepare_upload
    except ImportError as e:
        return f"❌ Uploads not available on this host (missing playwright). {e}"

    search_lower = search.lower().strip()
    words = [w for w in search_lower.split() if w]

    assignments = query("lms_assignments")

    num_tokens = [w for w in words if w.isdigit()]
    word_tokens = [w for w in words if not w.isdigit()]

    def matches_assignment(r):
        course_title = f"{r['course']} {r['title']}".lower()
        course_only = r["course"].lower()
        rnum = str(r.get("number", "")).strip()

        for n in num_tokens:
            if n != rnum:
                return False

        course_initials = _initials_of(course_only)
        combined_initials = _initials_of(f"{r['course']} {r['title']}")

        for w in word_tokens:
            if w in course_title:
                continue
            if w in course_initials:
                continue
            if w in combined_initials:
                continue
            return False

        return True

    matches = [r for r in assignments if matches_assignment(r)]

    if not matches and num_tokens:
        for r in assignments:
            course_title = f"{r['course']} {r['title']}".lower()
            course_initials = _initials_of(r["course"].lower())
            combined_initials = _initials_of(f"{r['course']} {r['title']}")
            if all(
                w in course_title or w in course_initials or w in combined_initials
                for w in word_tokens
            ):
                matches.append(r)

    if not matches:
        return f"❌ No assignment matches '{search}'."
    if len(matches) > 1:
        lines = [f"⚠️ Multiple assignments match '{search}':"]
        for m in matches[:8]:
            lines.append(f"• [{m['course']}] #{m['number']} {m['title']}")
        lines.append("")
        lines.append("Be more specific, e.g. `upload ai lab 7`")
        return "\n".join(lines)

    a = matches[0]

    course_b64 = _lookup_course_b64(a["course"])
    if not course_b64:
        return (
            f"❌ Could not determine course ID for '{a['course']}'.\n"
            "Try running `/refresh-lms` on your laptop first."
        )

    result = prepare_upload(str(staged_path), a)
    if not result.get("ok"):
        return f"❌ {result['error']}"

    global _PENDING_UPLOAD
    _PENDING_UPLOAD = {
        "staged_path": result["staged_path"],
        "assignment": a,
        "sha256": result["sha256"],
        "course_b64": course_b64,
    }

    return (
        f"⚠️ *Confirm upload:*\n"
        f"• Assignment: [{a['course']}] #{a['number']} {a['title']}\n"
        f"• Deadline: {a.get('deadline', 'N/A')}\n"
        f"• Status: {a.get('status', 'N/A')}\n"
        f"• Local file: `{result['original_path']}`\n"
        f"• Size: {result['size_mb']} MB\n"
        f"• Type: {result['kind']}\n"
        f"• SHA256: `{result['sha256'][:16]}...`\n\n"
        f"To proceed, reply with exactly:\n`CONFIRM UPLOAD`\n\n"
        f"Or `/cancel` to abort."
    )


def cmd_upload(args: list[str]) -> str:
    """Slash-command form: /upload <assignment search> <path>"""
    if len(args) < 2:
        return (
            "*Usage:*\n"
            "`/upload <assignment search> <path/to/file>`\n"
            "Or say: `upload my assignment 1` (uses Streamlit staged file)"
        )

    file_path = args[-1]
    if not (("/" in file_path) or file_path.lower().endswith(
        (".docx", ".doc", ".pdf", ".pptx", ".ppt", ".xlsx", ".xls",
         ".txt", ".zip", ".png", ".jpg", ".jpeg", ".gif", ".mp4"))):
        return "❌ Last argument must be a file path."

    search = " ".join(args[:-1]).strip()
    return _do_upload_staging(search, Path(file_path))


def cmd_confirm(args: list[str]) -> str:
    global _PENDING_UPLOAD
    if not _PENDING_UPLOAD:
        return "No pending upload. Use `/upload ...` first."

    try:
        from core.uploader import upload_to_assignment
    except ImportError as e:
        return f"❌ Uploader unavailable: {e}"

    staged = _PENDING_UPLOAD["staged_path"]
    a = _PENDING_UPLOAD["assignment"]
    course_b64 = _PENDING_UPLOAD.get("course_b64", "")

    result = upload_to_assignment(staged, a, course_b64=course_b64)
    _PENDING_UPLOAD = {}

    if not result.get("ok"):
        return f"❌ Upload failed: {result.get('error')}"

    msg = (
        f"✅ *Submitted*\n"
        f"• Assignment: [{a['course']}] #{a['number']} {a['title']}\n"
        f"• File: `{Path(staged).name}`\n"
    )
    if result.get("screenshot"):
        msg += f"• Screenshot: `{result['screenshot']}`\n"
    msg += "• Audit: `data/uploads.log`\n"
    return msg


def cmd_cancel(args: list[str]) -> str:
    global _PENDING_UPLOAD
    _PENDING_UPLOAD = {}
    return "Cancelled. No upload performed."


def cmd_help() -> str:
    return HELP_TEXT


# ---------- Natural language upload ----------

_UPLOAD_VERBS = [
    "upload", "submit", "send my", "send the", "turn in",
    "hand in", "post my", "file my",
]

_NOISE_WORDS = {
    "my", "the", "a", "an", "to", "for", "on", "into", "in",
    "lms", "portal", "system", "please", "pls", "kindly",
    "assignment", "assignments", "submission", "submissions",
    "file", "files", "document", "documents",
    "upload", "submit", "it", "this", "that",
}


def _parse_nl_upload(text: str) -> dict:
    if not text:
        return {"is_upload": False}
    t = text.lower().strip()
    if t.startswith("/"):
        return {"is_upload": False}

    matched_verb = None
    for verb in _UPLOAD_VERBS:
        if t.startswith(verb + " ") or t == verb:
            matched_verb = verb
            break
    if not matched_verb:
        return {"is_upload": False}

    rest = t[len(matched_verb):].strip()
    tokens = re.findall(r"[A-Za-z0-9]+", rest)
    if not tokens:
        return {"is_upload": True, "search": "",
                "number": None, "words": []}

    numbers = [tok for tok in tokens if tok.isdigit()]
    words = [tok for tok in tokens
             if not tok.isdigit() and tok not in _NOISE_WORDS]

    return {
        "is_upload": True,
        "search": " ".join(words + numbers).strip(),
        "number": numbers[0] if numbers else None,
        "words": words,
    }


def _newest_staged_file() -> "Path | None":
    staging = Path("data/uploads/staging")
    if not staging.exists():
        return None
    files = [f for f in staging.glob("*")
             if f.is_file() and f.name not in (".gitkeep", ".DS_Store")]
    if not files:
        return None
    return max(files, key=lambda f: f.stat().st_mtime)


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
    "/upload":        cmd_upload,
    "/confirm":       cmd_confirm,
    "/cancel":        cmd_cancel,
    "/help":          cmd_help,
    "/start":         cmd_help,
}

ARG_COMMANDS = {"/notes", "/download", "/upload", "/confirm", "/cancel"}


def handle(text: str) -> str:
    text = (text or "").strip()
    if not text:
        return "Send /help to see what I can do."

    if text.upper() == "CONFIRM UPLOAD":
        return cmd_confirm([])

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

    # --- Natural-language upload intent ---
    nl = _parse_nl_upload(text)
    if nl.get("is_upload"):
        staged = _newest_staged_file()
        if not staged:
            return (
                "❌ I understood you want to upload something, but no file "
                "is staged.\n\n"
                "Open the **📎 Attach a file for upload** panel in "
                "Streamlit, upload your file, then try again."
            )
        if not nl.get("search"):
            return (
                "❓ Which assignment should I upload to?\n\n"
                f"Staged file: `{staged.name}`\n"
                "Try: `upload my assignment 1`"
            )
        return _do_upload_staging(nl["search"], staged)

    # --- Deterministic shortcuts ---
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
