"""
Analyze a saved HTML snapshot and print tables + headers + sample rows.
Usage: python -m scripts.inspect_html data/snapshots/attendance.html
"""
import sys
from pathlib import Path
from bs4 import BeautifulSoup


def _cell_text(c):
    return c.get_text(" ", strip=True).replace("\n", " ")


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m scripts.inspect_html <path-to-html>")
        sys.exit(1)

    html = Path(sys.argv[1]).read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "lxml")

    print(f"\n=== {sys.argv[1]} ===\n")
    title = soup.find("title")
    print(f"<title>: {title.get_text(strip=True) if title else 'none'}")

    tables = soup.find_all("table")
    for i, t in enumerate(tables):
        tid = t.get("id") or t.get("class") or ""
        rows = t.find_all("tr")
        if not rows:
            print(f"\n[{i}] id={tid!r}  EMPTY")
            continue
        header = [_cell_text(c) for c in rows[0].find_all(["th", "td"])]
        print(f"\n[{i}] id={tid!r}  rows={len(rows)}")
        print(f"    header: {header}")
        # print up to 2 data rows
        for r in rows[1:3]:
            cells = [_cell_text(c) for c in r.find_all(["th", "td"])]
            print(f"    data  : {cells}")

    # selects
    print("\n--- <select> elements ---")
    for i, s in enumerate(soup.find_all("select")):
        sid = s.get("id") or s.get("name") or ""
        opts = [o.get_text(strip=True) for o in s.find_all("option")][:8]
        print(f"[{i}] id={sid!r}  options={opts}")


if __name__ == "__main__":
    main()
