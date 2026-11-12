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
    # LOINC long common name of 44261-6 (loinc.org/44261-6). It names the score, not an item.
    # Last changed in LOINC 2.73, so the 2.72 name is not confirmed (docs/gaps.md G9).
    total_score=Code("44261-6", "Patient Health Questionnaire 9 item (PHQ-9) total score [Reported]"),
    min_score=0,
    max_score=27,
)

GAD7 = Instrument(
    key="gad7",
    # LOINC long common name of 70274-6 (loinc.org/70274-6, read 2026-11-12). Last changed in
    # LOINC 2.73, so the 2.72 name is not confirmed (docs/gaps.md G9). Seven items, 0-3 each.
    total_score=Code("70274-6", "Generalized anxiety disorder 7 item (GAD-7) total score [Reported.PHQ]"),
    min_score=0,
    max_score=21,
)

PAIN_NRS = Instrument(
    key="pain_nrs",
    # LOINC long common name of 72514-3 (loinc.org/72514-3). It names the score, not the question.
    # Last changed in LOINC 2.82, so the 2.72 name is not confirmed (docs/gaps.md G9).
    total_score=Code("72514-3", "Pain severity - 0-10 verbal numeric rating [Score] - Reported"),
    min_score=0,
    max_score=10,
)

ODI = Instrument(
    key="odi",
    # LOINC long common name of 97909-6 (loinc.org/97909-6); added and last changed in 2.70,
    # so this is the 2.72 name. The score is the percentage 0-100. The questionnaire is
    # copyrighted (docs/licensing.md); only the score is carried.
    total_score=Code("97909-6", "Oswestry disability index score ODI"),
    min_score=0,
    max_score=100,
)

INSTRUMENTS: dict[str, Instrument] = {i.key: i for i in (PHQ9, GAD7, PAIN_NRS, ODI)}
