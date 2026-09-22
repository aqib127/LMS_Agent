"""
Print what's currently in the SQLite database.
Usage:
    python -m scripts.show_db
    python -m scripts.show_db attendance
"""
import sys
from core.storage import query, stats


def main():
    if len(sys.argv) > 1:
        kind = sys.argv[1]
        items = query(kind)
        print(f"\n=== {kind} ({len(items)} rows) ===")
        for item in items:
            print(f"  {item}")
    else:
        print("\n=== DB stats ===")
        for kind, n in stats().items():
            print(f"  {kind:20s} {n}")


if __name__ == "__main__":
    main()
