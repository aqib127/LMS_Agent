"""
Run all scrapers against the saved HTML snapshots in data/snapshots/.
Verifies parsing works before wiring them into live-scraping.
"""
import json
from pathlib import Path
from scrapers import (
    scrape_attendance, scrape_courses, scrape_exam_results,
    scrape_fee_challans, scrape_exam_seats, scrape_community_services,
)


TESTS = [
    ("attendance", "attendance.html", scrape_attendance),
    ("courses", "registered_courses.html", scrape_courses),
    ("exam_results", "exam_result.html", scrape_exam_results),
    ("fees", "fee_challans.html", scrape_fee_challans),
    ("exam_seats", "exam_seats.html", scrape_exam_seats),
    ("community_services", "community_services.html", scrape_community_services),
]


def main():
    snap_dir = Path("data/snapshots")
    for name, fname, fn in TESTS:
        f = snap_dir / fname
        if not f.exists():
            print(f"--- {name}: SKIP (no {f})")
            continue
        html = f.read_text(encoding="utf-8")
        try:
            items = fn(html)
        except Exception as e:
            print(f"--- {name}: ERROR {e}")
            continue
        print(f"\n=== {name} ({len(items)} items) ===")
        for item in items[:3]:
            print(f"  {item.model_dump()}")
        if len(items) > 3:
            print(f"  ... and {len(items) - 3} more")


if __name__ == "__main__":
    main()
