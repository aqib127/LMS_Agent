"""
Fetch fresh data from the LMS and store it in SQLite.
Usage:
    python -m scripts.refresh
"""
from core.scraper_runner import scrape_all_live
from core.storage import stats


def main():
    print("=== Live scrape starting ===")
    summary = scrape_all_live()

    print("\n=== Summary ===")
    for kind, s in summary.items():
        if "error" in s:
            print(f"  {kind:20s} ERROR: {s['error']}")
        else:
            print(f"  {kind:20s} total={s['total']:3d}  new={s['new']:3d}  changed={s['changed']:3d}")

    print("\n=== DB totals ===")
    for kind, n in stats().items():
        print(f"  {kind:20s} {n}")


if __name__ == "__main__":
    main()
