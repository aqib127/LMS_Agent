"""
SQLite storage for scraped data.
One table per entity type. Uses JSON blobs for simplicity.
"""
import json
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Any
from loguru import logger
from pydantic import BaseModel


DB_PATH = Path("data/lms.db")


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def init_db() -> None:
    """Create tables if they don't exist."""
    with _connect() as con:
        con.executescript("""
            CREATE TABLE IF NOT EXISTS scraped (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kind TEXT NOT NULL,
                key TEXT NOT NULL,
                payload TEXT NOT NULL,
                scraped_at TEXT NOT NULL,
                UNIQUE(kind, key)
            );

            CREATE INDEX IF NOT EXISTS idx_kind ON scraped(kind);

            CREATE TABLE IF NOT EXISTS runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                status TEXT NOT NULL,
                message TEXT
            );
        """)
    logger.debug("Database initialized")


def _make_key(item: BaseModel, kind: str) -> str:
    """Stable unique key per entity. Uses the most identifying field(s)."""
    d = item.model_dump()
    if kind == "attendance":
        return d.get("code", "")
    if kind == "courses":
        return d.get("code", "")
    if kind == "exam_results":
        return f"{d.get('semester','')}|{d.get('code','')}"
    if kind == "fees":
        return d.get("challan_no", "")
    if kind == "exam_seats":
        return f"{d.get('date','')}|{d.get('title','')}|{d.get('room','')}"
    if kind == "community_services":
        return f"{d.get('semester','')}|{d.get('organization','')}|{d.get('completed_date','')}"
    # LMS types
    if kind == "lms_assignments":
        return f"{d.get('course','')}|{d.get('number','')}"
    if kind == "lms_quizzes":
        return f"{d.get('course','')}|{d.get('number','')}"
    if kind == "lms_lecture_notes":
        return f"{d.get('course','')}|{d.get('week','')}"
    if kind == "lms_announcements":
        return f"{d.get('course','')}|{d.get('number','')}"
    if kind == "lms_papers":
        return f"{d.get('course','')}|{d.get('number','')}"
    if kind == "lms_course_outlines":
        return d.get("course", "")
    # fallback: full JSON
    return json.dumps(d, sort_keys=True)

def upsert_many(kind: str, items: list[BaseModel]) -> tuple[int, int]:
    """
    Insert new items, update changed ones. Returns (new_count, changed_count).
    Uses payload comparison to detect changes.
    """
    new_count = 0
    changed_count = 0
    now = datetime.utcnow().isoformat()

    with _connect() as con:
        for item in items:
            key = _make_key(item, kind)
            payload = json.dumps(item.model_dump(), default=str)
            row = con.execute(
                "SELECT payload FROM scraped WHERE kind = ? AND key = ?",
                (kind, key),
            ).fetchone()

            if row is None:
                con.execute(
                    "INSERT INTO scraped (kind, key, payload, scraped_at) VALUES (?, ?, ?, ?)",
                    (kind, key, payload, now),
                )
                new_count += 1
            elif row["payload"] != payload:
                con.execute(
                    "UPDATE scraped SET payload = ?, scraped_at = ? WHERE kind = ? AND key = ?",
                    (payload, now, kind, key),
                )
                changed_count += 1

    return new_count, changed_count


def query(kind: str) -> list[dict]:
    """Return all rows of a given kind."""
    with _connect() as con:
        rows = con.execute(
            "SELECT payload, scraped_at FROM scraped WHERE kind = ? ORDER BY id",
            (kind,),
        ).fetchall()
    return [json.loads(r["payload"]) for r in rows]


def stats() -> dict[str, int]:
    """Return count per kind."""
    with _connect() as con:
        rows = con.execute(
            "SELECT kind, COUNT(*) as n FROM scraped GROUP BY kind"
        ).fetchall()
    return {r["kind"]: r["n"] for r in rows}


def start_run() -> int:
    with _connect() as con:
        cur = con.execute(
            "INSERT INTO runs (started_at, status) VALUES (?, ?)",
            (datetime.utcnow().isoformat(), "running"),
        )
        return cur.lastrowid


def finish_run(run_id: int, status: str, message: str = "") -> None:
    with _connect() as con:
        con.execute(
            "UPDATE runs SET finished_at = ?, status = ?, message = ? WHERE id = ?",
            (datetime.utcnow().isoformat(), status, message, run_id),
        )
