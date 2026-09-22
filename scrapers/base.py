"""
Base helpers for all scrapers.
Each scraper takes an HTML string and returns a list of pydantic models.
"""
from bs4 import BeautifulSoup


def soup_of(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")


def text(el) -> str:
    return el.get_text(" ", strip=True).replace("\n", " ").strip() if el else ""


def cells(row) -> list[str]:
    return [text(c) for c in row.find_all(["th", "td"])]


def find_table_by_id(soup, table_id: str):
    """Find <table id="table_id"> or <table> with id containing that substring."""
    t = soup.find("table", id=table_id)
    if t:
        return t
    # fallback: substring match
    for t in soup.find_all("table"):
        tid = t.get("id", "")
        if table_id in tid:
            return t
    return None


def find_table_by_headers(soup, required_headers: list[str]):
    """Find first table whose first row contains all required header strings."""
    for t in soup.find_all("table"):
        rows = t.find_all("tr")
        if not rows:
            continue
        first_row_text = " | ".join(cells(rows[0])).lower()
        if all(h.lower() in first_row_text for h in required_headers):
            return t
    return None


def all_data_tables(soup, required_headers: list[str]):
    """Find ALL tables matching required headers (e.g. multiple semester tables)."""
    found = []
    for t in soup.find_all("table"):
        rows = t.find_all("tr")
        if not rows:
            continue
        first_row_text = " | ".join(cells(rows[0])).lower()
        if all(h.lower() in first_row_text for h in required_headers):
            found.append(t)
    return found


def to_float(s: str, default: float = 0.0) -> float:
    """Parse '2.33' or 'N/A' safely."""
    try:
        return float(s.strip())
    except Exception:
        return default


def to_int(s: str, default: int = 0) -> int:
    try:
        return int(s.strip())
    except Exception:
        return default
