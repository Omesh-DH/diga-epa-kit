"""Catalogue of standardised PROM instruments the library can export.

Scores and codes only: the kit carries the LOINC code of an instrument's
total score and its score range, never item wording, item codes or answer
texts (docs/decisions/0007-prom-scores-only.md).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Code:
    code: str
    display: str


@dataclass(frozen=True)
class Instrument:
    key: str
    total_score: Code
    min_score: int
    max_score: int


PHQ9 = Instrument(
    key="phq9",
    # LOINC 2.72 long common name of 44261-6 (loinc.org/44261-6). It names the score, not an item.
    total_score=Code("44261-6", "Patient Health Questionnaire 9 item (PHQ-9) total score [Reported]"),
    min_score=0,
    max_score=27,
)

INSTRUMENTS: dict[str, Instrument] = {i.key: i for i in (PHQ9,)}
