"""
The brain: turns raw scraped data into useful answers.
"""
from datetime import datetime, date, timedelta
from core.llm import chat, LLMError
from core.storage import query
from core.utils import logger
from config.settings import settings


SYSTEM_PROMPT = """You are a factual assistant for a Bahria University student.
You have access to their LMS data: attendance, courses, exam results, fees,
exam seats, assignments, quizzes, announcements, and lecture notes.

CRITICAL RULES:
- Answer using ONLY the provided data.
- Do NOT write "Here is the answer" or similar filler. Start directly with the facts.
- List items per-record. Never compute averages unless explicitly asked.
- If data is missing, say "I don't have that information."
- For attendance < 75%, add " ⚠️" after the percentage.
- For assignments past their deadline, add " ⏰" (overdue).
- Use bullet points with a leading • for multi-item answers."""


# ---------------------------------------------------------------------------
# CMS formatters
# ---------------------------------------------------------------------------

def _fmt_attendance() -> str:
    rows = query("attendance")
    if not rows:
        return "No attendance records."
    lines = ["ATTENDANCE:"]
    for r in rows:
        warn = " ⚠️" if r["percentage"] < 75 else ""
        lines.append(
            f"  {r['code']} {r['title']} — {r['percentage']}% "
            f"({r['present_hours']}/{r['total_hours']} hrs){warn}"
        )
    return "\n".join(lines)


def _fmt_courses() -> str:
    rows = query("courses")
    if not rows:
        return "No courses."
    lines = ["COURSES:"]
    for r in rows:
        lines.append(
            f"  {r['code']} {r['title']} — {r['credit_hours']} CH, "
            f"teacher {r['teacher']}, class {r['class_name']}"
        )
    return "\n".join(lines)


def _fmt_results() -> str:
    rows = query("exam_results")
    if not rows:
        return "No results."
    lines = ["EXAM RESULTS:"]
    for r in rows:
        lines.append(
            f"  {r['code']} {r['title']} — grade {r['grade']} "
            f"({r['grade_points']} pts, {r['credit_hours']} CH, {r['semester']})"
        )
    return "\n".join(lines)


def _fmt_fees() -> str:
    rows = query("fees")
    if not rows:
        return "No fee challans."
    lines = ["FEES:"]
    for r in rows:
        lines.append(
            f"  {r['semester']} — {r['amount']}, status {r['status']}, "
            f"due {r['due_date']}, deposit {r['deposit_date']}"
        )
    return "\n".join(lines)


def _fmt_exam_seats() -> str:
    rows = query("exam_seats")
    if not rows:
        return "No exam seats scheduled."
    lines = ["EXAM SEATS:"]
    for r in rows:
        lines.append(
            f"  {r['title']} — {r['date']} {r['start_time']} "
            f"(Room {r['room']}, Row {r['row']} Col {r['column']})"
        )
    return "\n".join(lines)


def _fmt_community() -> str:
    rows = query("community_services")
    if not rows:
        return ""
    lines = ["COMMUNITY SERVICES:"]
    for r in rows:
        if not r.get("organization"):
            continue
        lines.append(
            f"  {r['semester']} — {r['organization']} ({r['job_title']}), "
            f"{r['hours']} hours, {r['completed_date']}"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# LMS formatters
# ---------------------------------------------------------------------------

def _fmt_lms_assignments() -> str:
    rows = query("lms_assignments")
    if not rows:
        return "No assignments."
    lines = ["ASSIGNMENTS:"]
    for r in rows:
        lines.append(
            f"  [{r['course']}] #{r['number']} {r['title']} — "
            f"deadline {r['deadline']}, status {r['status']}"
        )
    return "\n".join(lines)


def _fmt_lms_quizzes() -> str:
    rows = query("lms_quizzes")
    if not rows:
        return "No quizzes."
    lines = ["QUIZZES:"]
    for r in rows:
        lines.append(f"  [{r['course']}] {r['title']} — marks {r['marks']}")
    return "\n".join(lines)


def _fmt_lms_announcements() -> str:
    rows = query("lms_announcements")
    if not rows:
        return "No announcements."
    lines = ["ANNOUNCEMENTS:"]
    for r in rows:
        body = r.get("body", "")[:120]
        lines.append(f"  [{r['course']}] {r['title']} ({r['posted_date']}) — {body}")
    return "\n".join(lines)


def _fmt_lms_notes() -> str:
    rows = query("lms_lecture_notes")
    if not rows:
        return "No lecture notes."
    lines = ["LECTURE NOTES:"]
    for r in rows[:40]:
        lines.append(f"  [{r['course']}] Wk {r['week']}: {r['title']}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Question → relevant-context router
# ---------------------------------------------------------------------------

TOPIC_KEYWORDS = {
    "attendance":    ["attendance", "attend", "present", "absent"],
    "results":       ["result", "grade", "gpa", "cgpa", "marks", "score"],
    "fees":          ["fee", "challan", "payment", "paid", "unpaid", "dues", "voucher"],
    "exams":         ["exam", "seating", "seat", "room", "midterm", "final"],
    "courses":       ["course", "subject", "teacher", "instructor", "credit"],
    "community":     ["community", "volunteer", "service", "hours"],
    "assignments":   ["assignment", "homework", "due", "deadline", "submit"],
    "quizzes":       ["quiz"],
    "announcements": ["announcement", "notice", "news", "posted"],
    "notes":         ["notes", "lecture", "slide", "material", "content"],
}


def _pick_topics(question: str) -> list[str]:
    q = question.lower()
    hits = []
    for topic, kws in TOPIC_KEYWORDS.items():
        if any(k in q for k in kws):
            hits.append(topic)
    return hits or [
        "attendance", "results", "fees", "exams", "courses",
        "assignments", "announcements",
    ]


def _build_context(question: str) -> str:
    topics = _pick_topics(question)
    logger.debug(f"LLM context topics: {topics}")
    chunks = []
    if "attendance"    in topics: chunks.append(_fmt_attendance())
    if "results"       in topics: chunks.append(_fmt_results())
    if "fees"          in topics: chunks.append(_fmt_fees())
    if "exams"         in topics: chunks.append(_fmt_exam_seats())
    if "courses"       in topics: chunks.append(_fmt_courses())
    if "community"     in topics: chunks.append(_fmt_community())
    if "assignments"   in topics: chunks.append(_fmt_lms_assignments())
    if "quizzes"       in topics: chunks.append(_fmt_lms_quizzes())
    if "announcements" in topics: chunks.append(_fmt_lms_announcements())
    if "notes"         in topics: chunks.append(_fmt_lms_notes())
    return "\n\n".join(c for c in chunks if c)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def answer(question: str) -> str:
    context = _build_context(question)
    user_prompt = f"""DATA:
{context}

QUESTION: {question}

Reply directly with the facts. No preamble, no "Here is the answer"."""
    try:
        return chat(SYSTEM_PROMPT, user_prompt)
    except LLMError as e:
        return f"LLM error: {e}"


# ---------------------------------------------------------------------------
# Built-in quick answers (no LLM needed)
# ---------------------------------------------------------------------------

def lowest_attendance(n: int = 3) -> str:
    items = query("attendance")
    items.sort(key=lambda x: x.get("percentage", 100))
    lines = ["*Lowest attendance:*"]
    for it in items[:n]:
        warn = " ⚠️" if it["percentage"] < 75 else ""
        lines.append(f"• {it['code']} — {it['title']}: {it['percentage']}%{warn}")
    return "\n".join(lines)


def unpaid_fees() -> str:
    items = query("fees")
    unpaid = [i for i in items if i.get("status") != "Paid"]
    if not unpaid:
        return "All fees are paid. ✅"
    lines = ["*Unpaid fees:*"]
    for it in unpaid:
        lines.append(
            f"• {it['semester']}: {it['amount']} — due {it['due_date']} ({it['status']})"
        )
    return "\n".join(lines)


def upcoming_exams() -> str:
    items = query("exam_seats")
    if not items:
        return "No exam seats scheduled."
    lines = ["*Scheduled exams:*"]
    for it in items:
        lines.append(
            f"• {it['title']} — {it['date']} at {it['start_time']} "
            f"(Room {it['room']}, Row {it['row']} Col {it['column']})"
        )
    return "\n".join(lines)


def recent_results() -> str:
    items = query("exam_results")
    graded = [i for i in items if i.get("grade") and i["grade"] != "N/A"]
    lines = [f"*Results ({len(graded)} graded):*"]
    for it in graded[-10:]:
        lines.append(f"• {it['code']} — {it['title']}: {it['grade']} ({it['grade_points']})")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Rich digest for email notifications
# ---------------------------------------------------------------------------

def digest(events: dict[str, list[dict]]) -> str:
    """
    Build a rich, categorized digest from new/changed items.
    events = {"attendance": [...], "lms_assignments": [...], ...}
    """
    if not any(events.values()):
        return ""

    today = date.today()
    soon = today + timedelta(days=2)
    L = settings.lms_base
    C = settings.cms_base

    sections = []   # list of (priority, title, lines)

    # ----- Fees -----
    fee_items = events.get("fees", [])
    if fee_items:
        lines = []
        has_unpaid = False
        for it in fee_items:
            status = it.get("status", "")
            emoji = "✅" if status.lower() == "paid" else "⚠️"
            if status.lower() != "paid":
                has_unpaid = True
            lines.append(
                f"  {emoji} {it.get('semester','')} — {it.get('amount','')} "
                f"— {status} (due {it.get('due_date','')})"
            )
        lines.append(f"     → Pay at: {C}/FeeManagement/FeeChallans")
        sections.append((2 if has_unpaid else 5, "💰 Fee updates", lines))

    # ----- Attendance warnings -----
    att_items = events.get("attendance", [])
    low_att = [i for i in att_items if i.get("percentage", 100) < 75]
    if low_att:
        lines = []
        for it in low_att:
            lines.append(
                f"  ⚠️ {it.get('code','')} — {it.get('title','')}: "
                f"{it.get('percentage','')}%"
            )
        lines.append(f"     → Details: {C}/ClassAttendance/StudentWiseAttendance.aspx")
        sections.append((1, "📉 Low attendance warning", lines))

    # ----- Exam results (new grades) -----
    result_items = events.get("exam_results", [])
    graded = [i for i in result_items if i.get("grade") and i["grade"] != "N/A"]
    if graded:
        lines = []
        for it in graded:
            lines.append(
                f"  🎓 {it.get('code','')} — {it.get('title','')}: "
                f"{it.get('grade','')} ({it.get('grade_points','')})"
            )
        lines.append(f"     → Full results: {C}/Exams/ExamResult.aspx")
        sections.append((1, "🎓 New grades posted", lines))

    # ----- Exam seats -----
    seat_items = events.get("exam_seats", [])
    if seat_items:
        lines = []
        for it in seat_items:
            lines.append(
                f"  📝 {it.get('title','')} — {it.get('date','')} "
                f"{it.get('start_time','')} (Room {it.get('room','')}, "
                f"Row {it.get('row','')} Col {it.get('column','')})"
            )
        lines.append(f"     → Seating plan: {C}/ExamSeatingPlan/ExamSeats")
        sections.append((2, "📝 Exam seats", lines))

    # ----- LMS Assignments -----
    a_items = events.get("lms_assignments", [])
    if a_items:
        new_a = [i for i in a_items if "exceeded" not in i.get("status", "").lower()]
        overdue_a = [i for i in a_items if "exceeded" in i.get("status", "").lower()]

        if new_a:
            lines = []
            for it in new_a:
                lines.append(
                    f"  📅 [{it.get('course','')}] {it.get('title','')} "
                    f"— due {it.get('deadline','')}"
                )
            lines.append(f"     → Assignments: {L}/Assignments.php")
            sections.append((1, "📚 New assignments", lines))

        if overdue_a:
            lines = []
            for it in overdue_a[:5]:
                lines.append(
                    f"  ⏰ [{it.get('course','')}] {it.get('title','')} "
                    f"— was due {it.get('deadline','')}"
                )
            if len(overdue_a) > 5:
                lines.append(f"  ... and {len(overdue_a) - 5} more overdue")
            lines.append(f"     → Assignments: {L}/Assignments.php")
            sections.append((1, "⏰ Overdue assignments", lines))

    # ----- LMS Announcements -----
    ann_items = events.get("lms_announcements", [])
    if ann_items:
        lines = []
        for it in ann_items:
            body = it.get("body", "")
            preview = body[:200] + "..." if len(body) > 200 else body
            lines.append(f"  📢 [{it.get('course','')}] {it.get('title','')}")
            lines.append(f"     Posted: {it.get('posted_date','')}")
            if preview:
                lines.append(f"     {preview}")
        lines.append(f"     → Announcements: {L}/Announcements.php")
        sections.append((2, "📢 New announcements", lines))

    # ----- LMS Lecture notes -----
    note_items = events.get("lms_lecture_notes", [])
    if note_items:
        lines = []
        by_course = {}
        for it in note_items:
            by_course.setdefault(it.get("course", ""), []).append(it)
        for course, items in by_course.items():
            titles = ", ".join(
                f"Wk {i.get('week','')}: {i.get('title','')}" for i in items[:3]
            )
            if len(items) > 3:
                titles += f", +{len(items) - 3} more"
            lines.append(f"  📄 [{course}] {titles}")
        lines.append(f"     → Lecture Notes: {L}/LectureNotes.php")
        sections.append((3, "📄 New lecture notes", lines))

    # ----- LMS Quizzes -----
    q_items = events.get("lms_quizzes", [])
    if q_items:
        lines = []
        for it in q_items:
            lines.append(
                f"  📝 [{it.get('course','')}] {it.get('title','')} "
                f"— marks: {it.get('marks','')}"
            )
        lines.append(f"     → Quizzes: {L}/Quizzes.php")
        sections.append((2, "📝 New quizzes", lines))

    # ----- Community services -----
    cs_items = events.get("community_services", [])
    if cs_items:
        lines = []
        for it in cs_items:
            if not it.get("organization"):
                continue
            lines.append(
                f"  🤝 {it.get('semester','')} — {it.get('organization','')} "
                f"({it.get('job_title','')}), {it.get('hours','')} hrs"
            )
        if lines:
            sections.append((4, "🤝 Community service updates", lines))

    # ----- Courses -----
    c_items = events.get("courses", [])
    if c_items:
        lines = []
        for it in c_items[:10]:
            lines.append(
                f"  📚 {it.get('code','')} — {it.get('title','')} "
                f"({it.get('credit_hours','')} CH, {it.get('teacher','')})"
            )
        lines.append(f"     → Courses: {C}/CourseRegistration/RegisteredCourses.aspx")
        sections.append((4, "📚 Registered courses", lines))

    if not sections:
        return ""

    sections.sort(key=lambda t: t[0])

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    body = [f"LMS Agent — digest ({now})", "=" * 60, ""]

    for priority, title, lines in sections:
        body.append(title.upper())
        body.extend(lines)
        body.append("")

    body.append("-" * 60)
    body.append("Reply to this email, or run `python -m scripts.chat` for details.")
    body.append(f"Portal: {C}/Dashboard.aspx")
    body.append(f"LMS:    {L}/Dashboard.php")

    return "\n".join(body)
