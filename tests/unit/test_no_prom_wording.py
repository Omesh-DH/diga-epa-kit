"""Licence guard: no questionnaire item wording or item-level codes in code, tests or synthetic data."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PHRASES = [
    line.strip().lower()
    for line in (ROOT / "docs" / "licensing" / "blocked-phrases.txt").read_text(encoding="utf-8").splitlines()
    if line.strip() and not line.startswith("#")
]
# LOINC codes of the PHQ-9 panel, its nine items and their answer list. The
# total score (44261-6) is the only PHQ-9 code the kit may carry. For the
# GAD-7 only the panel code (loinc.org/69737-5) is blocked: the public page
# does not list the item codes (docs/STATUS.md, open). Its total score
# (70274-6) is the only GAD-7 code the kit may carry.
ITEM_CODES = re.compile(r"\b(44249-1|4425\d-\d|44260-8|LA65(68|69|70|71)-\d|69737-5)\b")
TEXT_SUFFIXES = {".py", ".json", ".md", ".txt", ".csv", ".xml", ".yaml", ".yml", ".toml"}


def test_no_blocked_wording_or_item_codes():
    assert PHRASES
    hits = []
    for folder in ("src", "tests", "synthetic"):
        for path in (ROOT / folder).rglob("*"):
            if not path.is_file() or path.suffix not in TEXT_SUFFIXES or path == Path(__file__).resolve():
                continue
            text = path.read_text(encoding="utf-8")
            where = path.relative_to(ROOT)
            hits += [f"{where}: {p!r}" for p in PHRASES if p in text.lower()]
            hits += [f"{where}: code {m.group(0)}" for m in ITEM_CODES.finditer(text)]
    assert not hits, hits
