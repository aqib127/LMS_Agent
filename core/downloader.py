"""
Downloads files from the LMS using Playwright's HTTP client.

Uses page.context.request.get() which shares cookies with the browser
context, avoiding the ERR_ABORTED problem from page.goto() on download URLs.
"""
import re
from pathlib import Path
from urllib.parse import unquote
from core.auth import ensure_authenticated
from core.browser import browser_session
from core.utils import logger, ensure_dirs

DOWNLOADS_DIR = Path("data/downloads")
LMS_BASE = "https://lms.bahria.edu.pk/Student"
CMS_BRIDGE = "https://cms.bahria.edu.pk/Sys/Common/GoToLMS.aspx"


def _safe_name(s: str, max_len: int = 60) -> str:
    s = re.sub(r"[^\w\s\-.]", "", s)
    s = re.sub(r"\s+", "_", s.strip())
    return s[:max_len] or "file"


def _unique_path(directory: Path, stem: str, ext: str) -> Path:
    out = directory / f"{stem}{ext}"
    n = 1
    while out.exists():
        out = directory / f"{stem}_{n}{ext}"
        n += 1
    return out


def _filename_from_headers(headers: dict) -> str:
    cd = headers.get("content-disposition", "") or headers.get("Content-Disposition", "")
    if not cd:
        return ""
    m = re.search(r"filename\*=(?:UTF-8'')?([^;\r\n]+)", cd, re.IGNORECASE)
    if m:
        return unquote(m.group(1).strip().strip('"\''))
    m = re.search(r'filename="?([^";\r\n]+)"?', cd, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return ""


def download_file(rel_url: str, course: str = "misc", name: str = "file") -> Path:
    ensure_dirs()

    if rel_url.startswith("http"):
        url = rel_url
    else:
        rel_url = rel_url.lstrip("/")
        if rel_url.startswith("Student/"):
            rel_url = rel_url[len("Student/"):]
        url = f"{LMS_BASE}/{rel_url}"

    course_dir = DOWNLOADS_DIR / _safe_name(course)
    course_dir.mkdir(parents=True, exist_ok=True)

    with browser_session(use_auth=True, headless=True) as page:
        ensure_authenticated(page)
        page.goto(CMS_BRIDGE, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(4000)
        logger.info(f"On LMS: {page.url}")

        logger.info(f"Downloading: {url}")
        resp = page.context.request.get(url, timeout=60000, fail_on_status_code=False)

        if not resp.ok:
            raise RuntimeError(f"HTTP {resp.status} on {url}")

        body = resp.body()
        if not body:
            raise RuntimeError(f"Empty response on {url}")

        suggested = _filename_from_headers(resp.headers)
        if not suggested:
            suggested = url.split("/")[-1].split("?")[0] or "download"

        ext = Path(suggested).suffix.lower()
        if not ext:
            ext = Path(name).suffix.lower() or ".bin"

        stem = _safe_name(name) if name != "file" else _safe_name(Path(suggested).stem)
        out_path = _unique_path(course_dir, stem, ext)
        out_path.write_bytes(body)

        logger.info(
            f"Saved: {out_path} ({len(body)} bytes, "
            f"content-type={resp.headers.get('content-type', 'unknown')})"
        )
        return out_path


def list_downloads() -> list[Path]:
    if not DOWNLOADS_DIR.exists():
        return []
    files = [p for p in DOWNLOADS_DIR.rglob("*") if p.is_file()]
    return sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)
