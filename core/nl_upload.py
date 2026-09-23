"""
Natural-language upload intent parser.

Extracts an assignment identifier from free-form text like:
  "upload my assignment 1"
  "submit python basics"
  "upload ai lab 7 assignment"
  "send my ai lab journal"

Returns:
  {
    "is_upload": True,
    "search": "assignment 1",   # token string to match against DB
    "number": "1",              # extracted number or None
    "words": ["assignment"],    # non-number tokens
  }
or {"is_upload": False} if the text isn't an upload command.
"""
import re


# Verbs that mean "upload" in this context
UPLOAD_VERBS = [
    "upload", "submit", "send my", "send the", "turn in",
    "hand in", "put up", "post my", "file my",
]

# Words to strip from the search string
NOISE_WORDS = {
    "my", "the", "a", "an", "to", "for", "on", "into", "in",
    "lms", "portal", "system", "please", "pls", "kindly",
    "assignment", "assignments", "submission", "submissions",
    "file", "files", "document", "documents",
    "upload", "submit",
}


def parse_upload_intent(text: str) -> dict:
    """Return intent dict or {'is_upload': False}."""
    if not text:
        return {"is_upload": False}

    t = text.lower().strip()

    # Slash command already handled by bot.commands
    if t.startswith("/"):
        return {"is_upload": False}

    # Must start with an upload verb
    matched_verb = None
    for verb in UPLOAD_VERBS:
        if t.startswith(verb + " ") or t == verb:
            matched_verb = verb
            break
    if not matched_verb:
        return {"is_upload": False}

    # Strip the verb
    rest = t[len(matched_verb):].strip()

    # Extract tokens
    tokens = re.findall(r"[A-Za-z0-9]+", rest)
    if not tokens:
        return {"is_upload": False, "reason": "no_target"}

    numbers = [tok for tok in tokens if tok.isdigit()]
    words = [tok for tok in tokens if not tok.isdigit() and tok not in NOISE_WORDS]

    return {
        "is_upload": True,
        "search": " ".join(words + numbers).strip(),
        "number": numbers[0] if numbers else None,
        "words": words,
        "raw": text,
    }


def match_assignment(intent: dict, assignments: list) -> list:
    """
    Given the parsed intent and the list of assignment rows,
    return all matching assignment records (may be 0, 1, or many).
    """
    if not intent.get("is_upload"):
        return []

    num = intent.get("number")
    words = intent.get("words") or []

    def initials(s: str) -> str:
        ws = [w for w in re.split(r"\W+", s.lower()) if w]
        return "".join(w[0] for w in ws)

    matches = []
    for a in assignments:
        course = a.get("course", "")
        title = a.get("title", "")
        anum = str(a.get("number", "")).strip()

        haystack = f"{course} {title}".lower()
        course_initials = initials(course)
        combined_initials = initials(f"{course} {title}")

        # Number must match if user provided one
        if num is not None and num != anum:
            continue

        # Every word must appear in one of: haystack, initials, combined_initials
        ok = True
        for w in words:
            if (w in haystack) or (w in course_initials) \
                    or (w in combined_initials):
                continue
            ok = False
            break
        if not ok:
            continue

        matches.append(a)

    return matches


def newest_staged_file(staging_dir) -> "Path | None":
    """Return the newest file in staging, or None."""
    from pathlib import Path
    p = Path(staging_dir)
    if not p.exists():
        return None
    files = [f for f in p.glob("*")
             if f.is_file() and f.name not in (".gitkeep", ".DS_Store")]
    if not files:
        return None
    return max(files, key=lambda f: f.stat().st_mtime)
