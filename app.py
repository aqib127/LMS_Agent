"""
LMS Agent — Streamlit dashboard.
Run: streamlit run app.py
"""
import re
from datetime import date, datetime, timedelta
from pathlib import Path

import streamlit as st

from core.storage import query, stats, init_db
from core.ai_engine import (
    lowest_attendance, unpaid_fees, upcoming_exams, recent_results,
)
from core.utils import ensure_dirs
from core.formatters import clean_for_streamlit


# --- Page config ---
st.set_page_config(
    page_title="LMS Agent — Bahria University",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

ensure_dirs()
init_db()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
}


def parse_date(s: str):
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


def clean_deadline(s: str) -> str:
    """Extract only the first 'DD Month YYYY - HH:MM am/pm' from a deadline string."""
    if not s:
        return ""
    m = re.search(
        r"\d{1,2}\s+\w+\s+\d{4}\s*-\s*\d{1,2}:\d{2}\s*(?:am|pm)?",
        s, re.IGNORECASE,
    )
    return m.group(0) if m else s[:50]


def compute_gpa():
    rows = query("exam_results")
    graded = [r for r in rows if r.get("grade") and r["grade"] != "N/A"]
    if not graded:
        return None, 0, 0
    total_ch = sum(r["credit_hours"] for r in graded)
    total_pts = sum(r["product"] for r in graded)
    gpa = round(total_pts / total_ch, 2) if total_ch else 0.0
    return gpa, total_ch, len(graded)


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

st.sidebar.title("🎓 LMS Agent")
page = st.sidebar.radio(
    "Navigate",
    [
        "🏠 Dashboard",
        "⏰ Deadlines",
        "📊 Attendance",
        "🎓 Grades",
        "💰 Fees",
        "📚 Courses",
        "📄 Lecture Notes",
        "📥 Downloads",
        "📢 Announcements",
        "💬 Ask AI",
    ],
)

st.sidebar.markdown("---")
st.sidebar.caption(f"Updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

if st.sidebar.button("🔄 Refresh CMS", use_container_width=True):
    progress = st.sidebar.progress(10, text="Logging in...")
    try:
        from core.scraper_runner import scrape_all_live
        progress.progress(30, text="Scraping...")
        s = scrape_all_live()
        progress.progress(100, text="Done")
        total = sum(v.get("total", 0) for v in s.values() if "error" not in v)
        st.sidebar.success(f"✓ {total} items scraped")
    except Exception as e:
        st.sidebar.error(f"Failed: {e}")
    finally:
        progress.empty()

if st.sidebar.button("📥 Refresh LMS (slow)", use_container_width=True):
    progress = st.sidebar.progress(10, text="Logging in...")
    try:
        from core.lms_runner import scrape_lms_all
        progress.progress(30, text="Bridging to LMS...")
        s = scrape_lms_all()
        progress.progress(100, text="Done")
        total = sum(v.get("total", 0) for v in s.values())
        st.sidebar.success(f"✓ {total} items scraped")
    except Exception as e:
        st.sidebar.error(f"Failed: {e}")
    finally:
        progress.empty()


# ---------------------------------------------------------------------------
# Page: Dashboard
# ---------------------------------------------------------------------------

if page == "🏠 Dashboard":
    st.title("🏠 Dashboard")

    col1, col2, col3, col4 = st.columns(4)

    gpa, ch, n_graded = compute_gpa()
    col1.metric("GPA", f"{gpa}" if gpa else "—", f"{ch} CH graded")

    fees = query("fees")
    unpaid = [f for f in fees if f.get("status", "").lower() != "paid"]
    col2.metric("Unpaid fees", len(unpaid), f"{len(fees)} total")

    assignments = query("lms_assignments")
    upcoming_a = [a for a in assignments if "exceeded" not in a.get("status", "").lower()]
    col3.metric("Upcoming assignments", len(upcoming_a),
                f"{len(assignments) - len(upcoming_a)} overdue")

    att = query("attendance")
    low = [a for a in att if a.get("percentage", 100) < 75]
    col4.metric("Low attendance", len(low), f"{len(att)} courses")

    st.markdown("---")

    st.subheader("📅 Due in the next 7 days")
    today = date.today()
    week = today + timedelta(days=7)
    soon = []
    for a in assignments:
        d = parse_date(a.get("deadline", ""))
        if d and today <= d <= week:
            soon.append((d, a))
    soon.sort(key=lambda t: t[0])

    if soon:
        for d, a in soon:
            delta = (d - today).days
            when = "TODAY" if delta == 0 else ("TOMORROW" if delta == 1 else f"in {delta} days")
            st.write(f"📅 **{d.strftime('%d %b')}** — [{a['course']}] {a['title']} — *{when}*")
    else:
        st.success("Nothing due in the next 7 days ✅")

    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("💰 Unpaid fees")
        if unpaid:
            for f in unpaid:
                st.warning(
                    f"**{f['semester']}** — {f['amount']} — due {f['due_date']}"
                )
        else:
            st.success("All fees paid ✅")
    with c2:
        st.subheader("⚠️ Low attendance (< 75%)")
        if low:
            for a in low:
                st.error(f"**{a['code']}** — {a['title']}: {a['percentage']}%")
        else:
            st.success("All courses above 75% ✅")


# ---------------------------------------------------------------------------
# Page: Deadlines
# ---------------------------------------------------------------------------

elif page == "⏰ Deadlines":
    st.title("⏰ Deadlines")

    rows = query("lms_assignments")
    if not rows:
        st.info("No assignments yet. Click 'Refresh LMS' in the sidebar.")
    else:
        def is_overdue(r):
            return "exceeded" in r.get("status", "").lower()

        upcoming = sorted([r for r in rows if not is_overdue(r)],
                          key=lambda r: r.get("deadline", ""))
        overdue = sorted([r for r in rows if is_overdue(r)],
                         key=lambda r: r.get("deadline", ""), reverse=True)

        col1, col2 = st.columns(2)
        with col1:
            st.subheader(f"📅 Upcoming ({len(upcoming)})")
            if not upcoming:
                st.success("No upcoming assignments ✅")
            for r in upcoming:
                with st.container(border=True):
                    st.markdown(f"**[{r['course']}]** {r['title']}")
                    st.caption(f"Due: {clean_deadline(r['deadline'])}")
        with col2:
            st.subheader(f"⏰ Overdue ({len(overdue)})")
            if not overdue:
                st.success("No overdue assignments ✅")
            for r in overdue:
                with st.container(border=True):
                    st.markdown(f"🔴 **[{r['course']}]** {r['title']}")
                    st.caption(f"Was due: {clean_deadline(r['deadline'])}")


# ---------------------------------------------------------------------------
# Page: Attendance
# ---------------------------------------------------------------------------

elif page == "📊 Attendance":
    st.title("📊 Attendance")

    rows = query("attendance")
    if not rows:
        st.info("No attendance data. Click 'Refresh CMS' in the sidebar.")
    else:
        import pandas as pd
        df = pd.DataFrame([
            {
                "Code": r["code"],
                "Title": r["title"],
                "Present": r["present_hours"],
                "Absent": r["absent_hours"],
                "Total": r["total_hours"],
                "Percentage": r["percentage"],
            } for r in rows
        ]).sort_values("Percentage")

        low = df[df["Percentage"] < 75]
        if not low.empty:
            st.error(f"⚠️ {len(low)} course(s) below 75% attendance")

        st.bar_chart(df.set_index("Code")["Percentage"])

        st.dataframe(
            df.style.map(
                lambda v: "background-color: #fee" if isinstance(v, (int, float)) and v < 75 else "",
                subset=["Percentage"],
            ),
            use_container_width=True,
        )


# ---------------------------------------------------------------------------
# Page: Grades
# ---------------------------------------------------------------------------

elif page == "🎓 Grades":
    st.title("🎓 Grades")

    gpa, ch, n = compute_gpa()
    if gpa is None:
        st.info("No graded courses yet.")
    else:
        col1, col2, col3 = st.columns(3)
        col1.metric("Semester GPA", f"{gpa}")
        col2.metric("Graded courses", n)
        col3.metric("Credit hours", ch)

    rows = query("exam_results")
    if rows:
        import pandas as pd
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No exam results yet. Click 'Refresh CMS'.")


# ---------------------------------------------------------------------------
# Page: Fees
# ---------------------------------------------------------------------------

elif page == "💰 Fees":
    st.title("💰 Fees")

    rows = query("fees")
    if not rows:
        st.info("No fee data. Click 'Refresh CMS'.")
    else:
        for r in rows:
            status = r.get("status", "")
            if status.lower() == "paid":
                st.success(
                    f"✅ **{r['semester']}** — {r['amount']} — Paid on {r.get('deposit_date', 'N/A')}"
                )
            else:
                st.warning(
                    f"⚠️ **{r['semester']}** — {r['amount']} — {status}, due {r['due_date']}"
                )


# ---------------------------------------------------------------------------
# Page: Courses
# ---------------------------------------------------------------------------

elif page == "📚 Courses":
    st.title("📚 Registered Courses")

    rows = query("courses")
    if not rows:
        st.info("No courses. Click 'Refresh CMS'.")
    else:
        import pandas as pd
        df = pd.DataFrame([
            {
                "Code": r["code"],
                "Title": r["title"],
                "Credit Hours": r["credit_hours"],
                "Class": r["class_name"],
                "Teacher": r["teacher"],
                "Email": r["teacher_email"],
            } for r in rows
        ])
        st.dataframe(df, use_container_width=True)


# ---------------------------------------------------------------------------
# Page: Lecture Notes
# ---------------------------------------------------------------------------

elif page == "📄 Lecture Notes":
    st.title("📄 Lecture Notes")

    rows = query("lms_lecture_notes")
    if not rows:
        st.info("No lecture notes. Click 'Refresh LMS' in the sidebar.")
    else:
        courses = sorted(set(r["course"] for r in rows))
        chosen = st.selectbox("Choose a course", courses)
        filtered = [r for r in rows if r["course"] == chosen]
        for r in filtered:
            with st.container(border=True):
                st.markdown(f"**Week {r['week']}** — {r['title']}")
                if r.get("files_url"):
                    st.caption("📥 has downloadable file")


# ---------------------------------------------------------------------------
# Page: Downloads
# ---------------------------------------------------------------------------

elif page == "📥 Downloads":
    st.title("📥 Downloads")

    from core.downloader import download_file, list_downloads

    tab1, tab2 = st.tabs(["📄 Available files", "📁 Downloaded files"])

    with tab1:
        # Gather all downloadable items across kinds
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
            if r.get("solution_url"):
                items.append({
                    "kind": "assignments",
                    "course": r["course"],
                    "name": f"#{r['number']} — {r['title']}",
                    "url": r["solution_url"],
                })
        for r in query("lms_quizzes"):
            if r.get("quiz_url"):
                items.append({
                    "kind": "quizzes",
                    "course": r["course"],
                    "name": f"#{r['number']} — {r['title']}",
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

        if not items:
            st.info("No downloadable files found. Run 'Refresh LMS' first.")
        else:
            # Filter controls
            c1, c2 = st.columns(2)
            with c1:
                kinds = sorted(set(i["kind"] for i in items))
                kind_choice = st.selectbox("Kind", ["All"] + kinds)
            with c2:
                courses = sorted(set(i["course"] for i in items))
                course_choice = st.selectbox("Course", ["All"] + courses)

            filtered = items
            if kind_choice != "All":
                filtered = [i for i in filtered if i["kind"] == kind_choice]
            if course_choice != "All":
                filtered = [i for i in filtered if i["course"] == course_choice]

            st.caption(f"{len(filtered)} file(s)")

            # Show files with download buttons
            for i, it in enumerate(filtered):
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.markdown(f"`[{it['kind']}]` **{it['course']}** — {it['name']}")
                with col2:
                    if st.button("⬇️", key=f"dl_{i}", help="Download"):
                        with st.spinner("Downloading..."):
                            try:
                                path = download_file(
                                    rel_url=it["url"],
                                    course=it["course"],
                                    name=it["name"],
                                )
                                st.success(f"Saved `{path.name}`")
                            except Exception as e:
                                st.error(f"Failed: {e}")

    with tab2:
        st.subheader("Files already downloaded")
        files = list_downloads()
        if not files:
            st.info("No files downloaded yet. Use the first tab.")
        else:
            st.caption(f"{len(files)} file(s)")
            for p in files:
                size_kb = p.stat().st_size // 1024
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.write(f"📄 `{p.relative_to('data/downloads')}` — {size_kb} KB")
                with col2:
                    with open(p, "rb") as f:
                        st.download_button(
                            "💾 Save",
                            data=f,
                            file_name=p.name,
                            key=f"save_{p}",
                        )


# ---------------------------------------------------------------------------
# Page: Announcements
# ---------------------------------------------------------------------------

elif page == "📢 Announcements":
    st.title("📢 Announcements")

    rows = query("lms_announcements")
    if not rows:
        st.info("No announcements. Click 'Refresh LMS'.")
    else:
        for r in rows:
            with st.expander(f"📢 [{r['course']}] {r['title']}  —  {r['posted_date']}"):
                st.write(r.get("body", ""))


# ---------------------------------------------------------------------------
# Page: Ask AI
# ---------------------------------------------------------------------------

elif page == "💬 Ask AI":
    st.title("💬 Ask the LMS Agent")
    st.caption("Ask anything about your attendance, grades, deadlines, fees, notes, etc.")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Render last 30 messages
    for role, msg in st.session_state.chat_history[-30:]:
        with st.chat_message(role):
            st.markdown(clean_for_streamlit(msg))

    prompt = st.chat_input("Ask a question...")
    if prompt:
        st.session_state.chat_history.append(("user", prompt))
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                from bot.commands import handle
                try:
                    reply = handle(prompt)
                except Exception as e:
                    reply = f"❌ Error: {e}"
            st.markdown(clean_for_streamlit(reply))
        st.session_state.chat_history.append(("assistant", reply))
