# 0007 PROMs: scores and codes only

Addendum 2026-11-12: a single-item rating such as the 0–10 pain rating
(LOINC 72514-3) counts as a score. Its code names the rating, and the
anchor texts of the scale are still not carried.

Date: 2026-11-11. Status: accepted (user decision). Supersedes 0006.

## Context

The agreed plan rules out questionnaire item wording in code, tests and
data: scores and codes only. The first PHQ-9 mapping exported a
`Questionnaire` and one `QuestionnaireResponse` per completion. Their item
codes need a `display` (the profile sets `display` min 1 wherever a code is
given), and LOINC's display names for the PHQ-9 items paraphrase the item
wording. PHQ-9 is free to use, but most other instruments are not, and one
rule for every instrument is simpler to keep.

## Decision

- A PROM entry in the input is instrument, completion time and total score.
  Item answers are not accepted.
- The kit exports one `KBV_PR_MIO_DIGA_Observation_Score_or_Assessment_by_Scale`
  per completion, in section *Beurteilungen*. It carries the LOINC code of
  the total score and the scale bounds as `referenceRange`.
- No `Questionnaire`, no `QuestionnaireResponse`, no *Fragebögen* section, no
  `Observation.derivedFrom`.
- The instrument catalogue holds only the total-score code and the score range.
- `tests/unit/test_no_prom_wording.py` fails if a fragment listed in
  `docs/licensing/blocked-phrases.txt` appears in `src/`, `tests/` or `synthetic/`.

## Consequences

- Receivers see the score and its range, not the individual answers. A
  manufacturer that wants to export answers has to add that outside the kit
  and clear the instrument's licence itself.
- The Questionnaire canonical question (0006) no longer applies.
- Mapped profiles drop from 10 to 8 of 44.
- For the cost study: the effort already logged for the Questionnaire
  mapping stays in `research/timelog.csv` as a dead end.
