"""Catalogue of standardised PROM instruments the library can export.

Codes and displays are LOINC (version pinned by the active version pack);
item texts are the LOINC displays, not the licensed German instrument wording.
A manufacturer with rights to a localised text can swap ``text`` per item.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Code:
    code: str
    display: str


@dataclass(frozen=True)
class AnswerOption:
    code: Code
    score: int


@dataclass(frozen=True)
class Item:
    link_id: str
    code: Code


@dataclass(frozen=True)
class Instrument:
    key: str
    language: str
    panel: Code
    total_score: Code
    items: tuple[Item, ...]
    answers: tuple[AnswerOption, ...]

    @property
    def url(self) -> str:
        # LOINC's canonical form for questionnaires derived from a panel code
        return f"http://loinc.org/q/{self.panel.code}"

    def answer(self, score: int) -> AnswerOption:
        for a in self.answers:
            if a.score == score:
                return a
        raise ValueError(f"{self.key}: no answer with score {score}")

    @property
    def max_score(self) -> int:
        return len(self.items) * max(a.score for a in self.answers)


_FREQUENCY_2W = (
    AnswerOption(Code("LA6568-5", "Not at all"), 0),
    AnswerOption(Code("LA6569-3", "Several days"), 1),
    AnswerOption(Code("LA6570-1", "More than half the days"), 2),
    AnswerOption(Code("LA6571-9", "Nearly every day"), 3),
)

PHQ9 = Instrument(
    key="phq9",
    language="en",
    panel=Code("44249-1", "PHQ-9 quick depression assessment panel [Reported.PHQ]"),
    total_score=Code("44261-6", "Patient Health Questionnaire 9 item (PHQ-9) total score [Reported]"),
    items=tuple(
        Item(f"q{i}", Code(code, display))
        for i, (code, display) in enumerate(
            [
                ("44250-9", "Little interest or pleasure in doing things in last 2 weeks"),
                ("44255-8", "Feeling down, depressed, or hopeless in last 2 weeks"),
                ("44259-0", "Trouble falling or staying asleep, or sleeping too much in last 2 weeks"),
                ("44254-1", "Feeling tired or having little energy in last 2 weeks"),
                ("44251-7", "Poor appetite or overeating in last 2 weeks"),
                (
                    "44258-2",
                    "Feeling bad about yourself-or that you are a failure or have let yourself or your family"
                    " down in last 2 weeks",
                ),
                (
                    "44252-5",
                    "Trouble concentrating on things, such as reading the newspaper or watching television"
                    " in last 2 weeks",
                ),
                (
                    "44253-3",
                    "Moving or speaking so slowly that other people could have noticed. Or the opposite-being"
                    " so fidgety or restless that you have been moving around a lot more than usual in last"
                    " 2 weeks",
                ),
                (
                    "44260-8",
                    "Thoughts that you would be better off dead, or of hurting yourself in some way in last 2 weeks",
                ),
            ],
            start=1,
        )
    ),
    answers=_FREQUENCY_2W,
)

INSTRUMENTS: dict[str, Instrument] = {i.key: i for i in (PHQ9,)}
