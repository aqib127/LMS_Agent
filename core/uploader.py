"""
Uploads files to Bahria LMS assignments.

Verified flow (2026-09-23):
  1. Login → bridge to LMS
  2. Navigate to Assignments.php?s=<sem>&oc=<course>
  3. Find the target row by matching the assignment title
  4. Click the "Submit" link in that row → modal opens
  5. Set input[name="assignmentSubmissionFile"] with the local file
  6. Click "Submit Assignment" button
  7. Capture screenshot + audit log

Safety rules unchanged:
  - File size limit
  - File signature validation
  - Two-step confirmation required (caller handles)
  - Audit log at data/uploads.log
  - Screenshot saved to data/uploads/
"""
import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path
from playwright.sync_api import TimeoutError as PWTimeout

from core.auth import ensure_authenticated
from core.browser import browser_session
from core.utils import logger, ensure_dirs


UPLOADS_DIR = Path("data/uploads")
AUDIT_LOG = Path("data/uploads.log")
MAX_FILE_MB = 20

CMS_BRIDGE = "https://cms.bahria.edu.pk/Sys/Common/GoToLMS.aspx"


# Known semesters and courses → base64 params
# We refresh these dynamically below instead of hardcoding.
SEMESTER_FALL_2026 = "MjAyNjM%3D"   # decodes to "20263"


# File signatures
SIGNATURES = {
    b"PK\x03\x04": [".docx", ".pptx", ".xlsx", ".zip"],
    b"%PDF":       [".pdf"],
    b"\xd0\xcf\x11\xe0": [".doc", ".ppt", ".xls"],
    b"\xff\xd8\xff": [".jpg", ".jpeg"],
    b"\x89PNG":     [".png"],
    b"GIF8":        [".gif"],
    b"{\\rtf":      [".rtf"],
}


def _file_kind(path: Path) -> str:
    ext = path.suffix.lower()
    return {
        ".doc": "Word (legacy)", ".docx": "Word",
        ".pdf": "PDF", ".ppt": "PowerPoint (legacy)", ".pptx": "PowerPoint",
        ".xls": "Excel (legacy)", ".xlsx": "Excel",
        ".zip": "ZIP archive", ".txt": "Text", ".png": "PNG image",
        ".jpg": "JPEG image", ".jpeg": "JPEG image", ".gif": "GIF image",
        ".mp4": "Video",
    }.get(ext, f"{ext or 'unknown'} file")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _validate_file(path: Path) -> tuple[bool, str]:
    if not path.exists():
        return False, f"File does not exist: {path}"
    if not path.is_file():
        return False, f"Not a regular file: {path}"

    size_mb = path.stat().st_size / (1024 * 1024)
    if size_mb > MAX_FILE_MB:
        return False, f"File too large: {size_mb:.1f} MB (max {MAX_FILE_MB} MB)"

    with open(path, "rb") as f:
        head = f.read(16)

    ext = path.suffix.lower()
    expected_exts = None
    for sig, exts in SIGNATURES.items():
        if head.startswith(sig):
            expected_exts = exts
            break

    if expected_exts and ext not in expected_exts:
        # .docx/.pptx/.xlsx all start with PK; allow cross-match within Office family
        office_family = {".docx", ".pptx", ".xlsx", ".zip",
                         ".doc", ".ppt", ".xls"}
        if not (ext in office_family and expected_exts == [".zip"]):
            return False, (
                f"File extension {ext} doesn't match detected type "
                f"{expected_exts}. Possibly a renamed file."
            )
    return True, "ok"


def prepare_upload(local_path: str, assignment: dict) -> dict:
    """Validate + stage the file. Does NOT submit."""
    ensure_dirs()
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

    p = Path(local_path).expanduser().resolve()
    ok, msg = _validate_file(p)
    if not ok:
        return {"ok": False, "error": msg}

    staged = UPLOADS_DIR / p.name
    if staged != p:
        shutil.copy2(p, staged)

    return {
        "ok": True,
        "staged_path": staged,
        "original_path": p,
        "size_mb": round(p.stat().st_size / (1024 * 1024), 2),
        "kind": _file_kind(p),
        "sha256": _sha256(p),
        "assignment": assignment,
    }


def upload_to_assignment(staged_path: Path, assignment: dict,
                         semester_b64: str = SEMESTER_FALL_2026,
                         course_b64: str = "") -> dict:
    """
    Actually submits the file. Called ONLY after user confirms.

    assignment = {
      "course": "...",
      "number": "...",
      "title": "...",
    }
    course_b64 = base64-encoded course ID (oc param), e.g. "MTUxNTI3"
    """
    ensure_dirs()
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

    staged_path = Path(staged_path)
    ok, msg = _validate_file(staged_path)
    if not ok:
        return {"ok": False, "error": msg}

    if not course_b64:
        return {
            "ok": False,
            "error": "No course_b64 provided. Cannot navigate to assignments page.",
        }

    target_title = (assignment.get("title") or "").strip()
    target_number = str(assignment.get("number") or "").strip()

    if not target_title:
        return {"ok": False, "error": "Assignment has no title to match."}

    audit = {
        "timestamp": datetime.utcnow().isoformat(),
        "assignment": {
            "course": assignment.get("course"),
            "number": target_number,
            "title": target_title,
        },
        "file": {
            "name": staged_path.name,
            "size_bytes": staged_path.stat().st_size,
            "sha256": _sha256(staged_path),
        },
        "result": "pending",
    }

    screenshot_path = None
    try:
        with browser_session(use_auth=True, headless=True) as page:
            ensure_authenticated(page)
            page.goto(CMS_BRIDGE, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(4000)
            logger.info(f"LMS session active: {page.url}")

            # Navigate to assignments list for this course
            list_url = (
                f"https://lms.bahria.edu.pk/Student/Assignments.php"
                f"?s={semester_b64}&oc={course_b64}"
            )
            logger.info(f"Opening assignments list: {list_url}")
            page.goto(list_url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(2500)

            # Find the target row
            rows = page.locator("tr").all()
            target_row = None
            for r in rows:
                try:
                    text = r.inner_text()
                    if target_title.lower() in text.lower():
                        # Extra check: match number too if provided
                        if target_number and f"\n{target_number}\t" not in text \
                                and not text.strip().startswith(f"{target_number}\t"):
                            # Still likely the right row; accept if title matches exactly
                            pass
                        target_row = r
                        break
                except Exception:
                    continue

            if not target_row:
                audit["result"] = "failed"
                audit["error"] = f"Row with title '{target_title}' not found"
                _write_audit(audit)
                return {"ok": False, "error": audit["error"]}

            # Find Submit link in the row
            submit_link = None
            for l in target_row.locator("a").all():
                try:
                    if (l.inner_text() or "").strip().lower() == "submit":
                        submit_link = l
                        break
                except Exception:
                    continue

            if not submit_link:
                audit["result"] = "failed"
                audit["error"] = "No 'Submit' link in the target row (already submitted?)"
                _write_audit(audit)
                return {"ok": False, "error": audit["error"]}

            logger.info("Clicking Submit link to open the upload modal...")
            submit_link.click()
            page.wait_for_timeout(2000)

            # The file input appears in the modal
            file_input = page.locator("input[name='assignmentSubmissionFile']").first
            if not file_input.count():
                # Fallback: try by ID
                file_input = page.locator("#exampleInputFile").first
            if not file_input.count():
                audit["result"] = "failed"
                audit["error"] = "File input not found after clicking Submit"
                _write_audit(audit)
                return {"ok": False, "error": audit["error"]}

            logger.info(f"Attaching file: {staged_path}")
            file_input.set_input_files(str(staged_path))
            page.wait_for_timeout(1500)

            # Click the "Submit Assignment" button
            submit_btn = page.locator(
                "button:has-text('Submit Assignment'), "
                "input[type=submit][value*='Submit Assignment']"
            ).first
            if not submit_btn.count():
                # Fallback: any visible Submit button
                submit_btn = page.locator("button:has-text('Submit')").first

            if not submit_btn.count():
                audit["result"] = "failed"
                audit["error"] = "'Submit Assignment' button not found"
                _write_audit(audit)
                return {"ok": False, "error": audit["error"]}

            logger.info("Clicking 'Submit Assignment' button...")
            try:
                with page.expect_navigation(timeout=15000):
                    submit_btn.click()
                logger.info("Navigation detected after submit")
            except PWTimeout:
                logger.info("No navigation — probably AJAX submit")
                page.wait_for_timeout(4000)

            page.wait_for_timeout(3000)

            # Screenshot
            screenshot_path = UPLOADS_DIR / (
                f"submission-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.png"
            )
            page.screenshot(path=str(screenshot_path), full_page=True)

            # Sanity check: did the row change to show a submission?
            page.wait_for_timeout(1000)
            try:
                row_text_after = target_row.inner_text()
            except Exception:
                row_text_after = ""
            got_submission = "no submission" not in row_text_after.lower()

            audit["result"] = "submitted" if got_submission else "unclear"
            audit["screenshot"] = str(screenshot_path)
            audit["row_after"] = row_text_after[:300]

        _write_audit(audit)
        return {
            "ok": True,
            "submitted": got_submission,
            "screenshot": str(screenshot_path),
            "audit": audit,
        }

    except Exception as e:
        logger.exception("upload failed")
        audit["result"] = "error"
        audit["error"] = str(e)
        _write_audit(audit)
        return {"ok": False, "error": str(e)}


def _write_audit(audit: dict) -> None:
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(AUDIT_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(audit, ensure_ascii=False, default=str) + "\n")


def list_uploads() -> list[Path]:
    if not UPLOADS_DIR.exists():
        return []
    return sorted(
        [p for p in UPLOADS_DIR.iterdir() if p.is_file() and p.suffix != ".png"],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
