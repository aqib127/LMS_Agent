"""
Shared helpers for LMS scraping.

The LMS uses URL params: Assignments.php?s=<semester_b64>&oc=<course_b64>
"""
import base64
import urllib.parse
from pathlib import Path
from playwright.sync_api import Page
from loguru import logger
from core.auth import ensure_authenticated
from core.browser import browser_session
from core.utils import ensure_dirs
from bs4 import BeautifulSoup


LMS_BASE = "https://lms.bahria.edu.pk/Student"


def _cell_text(c) -> str:
    return c.get_text(" ", strip=True).replace("\n", " ")


def cells(row) -> list[str]:
    return [_cell_text(c) for c in row.find_all(["th", "td"])]


def soup_of(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")


def find_main_table(soup: BeautifulSoup):
    """Return the first table with more than 2 rows (the data table)."""
    for t in soup.find_all("table"):
        if len(t.find_all("tr")) > 2:
            return t
    return None


def decode_b64(s: str) -> str:
    """Decode URL-encoded base64."""
    try:
        raw = urllib.parse.unquote(s)
        # pad to multiple of 4
        raw += "=" * (-len(raw) % 4)
        return base64.b64decode(raw).decode("utf-8", errors="replace")
    except Exception:
        return s


def get_semesters(page: Page, page_path: str) -> list[dict]:
    """
    Return [{"label": "Fall-2026", "value": "...", "id": "20263"}] from any page.
    page_path example: 'Assignments.php'
    """
    page.goto(f"{LMS_BASE}/{page_path}", wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(1500)
    opts = page.eval_on_selector_all(
        "#semesterId option",
        "opts => opts.map(o => ({value: o.value, text: o.textContent.trim()}))",
    )
    return [
        {"label": o["text"], "value": o["value"], "id": decode_b64(o["value"])}
        for o in opts if o["value"]
    ]


def get_courses(page: Page, page_path: str, semester_b64: str) -> list[dict]:
    """
    Return [{"label": "Operating Systems Lab", "value": "...", "id": "..."}].
    """
    url = f"{LMS_BASE}/{page_path}?s={semester_b64}"
    page.goto(url, wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(1500)
    opts = page.eval_on_selector_all(
        "#courseId option",
        "opts => opts.map(o => ({value: o.value, text: o.textContent.trim()}))",
    )
    return [
        {"label": o["text"], "value": o["value"], "id": decode_b64(o["value"])}
        for o in opts if o["value"]  # skip empty "Select Course"
    ]


def fetch_page(page: Page, page_path: str, semester_b64: str, course_b64: str) -> str:
    """Fetch a page with semester + course selected. Returns HTML."""
    url = f"{LMS_BASE}/{page_path}?s={semester_b64}&oc={course_b64}"
    page.goto(url, wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(1200)
    return page.content()
