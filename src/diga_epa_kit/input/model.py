"""Input model: the data a DiGA typically holds, independent of FHIR."""

from __future__ import annotations

import unicodedata
from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, StrictInt, model_validator


class _Strict(BaseModel):
    model_config = {"extra": "forbid", "frozen": True}


class Manufacturer(_Strict):
    name: str
    website: str | None = None


class DigaInfo(_Strict):
    name: str
    ve_id: str = Field(description="DiGA-VE-ID (Verordnungseinheit) from the BfArM directory")
    pzn: str = Field(pattern=r"^\d{8}$")
    manufacturer: Manufacturer


class PatientInfo(_Strict):
    id: UUID = Field(description="Stable pseudonymous patient key inside the DiGA")
    birth_date: date | None = None
    gender: Literal["male", "female", "unknown"] | None = None


class BodyWeight(_Strict):
    measured_at: datetime
    kg: float = Field(gt=0, lt=700)
    method: Literal["measured", "self_reported"] = "measured"

    @model_validator(mode="after")
    def _tz_aware(self) -> "BodyWeight":
        # FHIR dateTime with a time part must carry a timezone offset.
        if self.measured_at.tzinfo is None:
            raise ValueError("measured_at needs a timezone offset")
        return self


class BloodPressure(_Strict):
    """One reading in mmHg. The bounds are plausibility limits, not clinical ones."""

    measured_at: datetime
    systolic: StrictInt = Field(ge=40, le=300)
    diastolic: StrictInt = Field(ge=20, le=200)

    @model_validator(mode="after")
    def _check(self) -> "BloodPressure":
        if self.measured_at.tzinfo is None:
            raise ValueError("measured_at needs a timezone offset")
        if self.diastolic >= self.systolic:
            raise ValueError("diastolic must be below systolic")
        return self


class DiaryEntry(_Strict):
    """Free text the patient wrote in the DiGA. It leaves the DiGA verbatim."""

    written_at: datetime
    # The length cap is the kit's own limit to keep documents small, not a profile rule.
    text: str = Field(min_length=1, max_length=5000)

    @model_validator(mode="after")
    def _check(self) -> "DiaryEntry":
        if self.written_at.tzinfo is None:
            raise ValueError("written_at needs a timezone offset")
        # A FHIR string must hold non-whitespace content and no surrounding whitespace.
        if self.text != self.text.strip():
            raise ValueError("text must not be blank or padded with whitespace")
        # FHIR strings allow no control characters except tab, CR and LF.
        if any(ord(c) < 32 and c not in "\t\n\r" for c in self.text):
            raise ValueError("text contains control characters")
        # Letters, digits, punctuation or symbols: something a reader can see.
        if not any(unicodedata.category(c)[0] in "LNPS" for c in self.text):
            raise ValueError("text has no visible character")
        return self


def _plain_text(value: str, what: str) -> None:
    """Same rules as a FHIR string: visible content, no padding, no control characters."""
    if value != value.strip():
        raise ValueError(f"{what} must not be blank or padded with whitespace")
    if any(ord(c) < 32 and c not in "\t\n\r" for c in value):
        raise ValueError(f"{what} contains control characters")
    if not any(unicodedata.category(c)[0] in "LNPS" for c in value):
        raise ValueError(f"{what} has no visible character")


class Goal(_Strict):
    """A goal the patient pursues in the DiGA, in free text."""

    # The DiGA's own key for the goal; care plans refer to it. It is not exported.
    id: str = Field(pattern=r"^[A-Za-z0-9._-]{1,64}$")
    description: str = Field(min_length=1, max_length=500)
    # No default: a missing status must not turn into a statement about the patient.
    status: Literal["active", "on_hold", "completed", "cancelled"]
    start: date
    end: date | None = None
    # True only if the DiGA knows the patient set the goal themselves.
    set_by_patient: bool = False

    @model_validator(mode="after")
    def _check(self) -> "Goal":
        _plain_text(self.description, "description")
        if self.end is not None and self.end < self.start:
            raise ValueError("end is before start")
        return self


class PlannedActivity(_Strict):
    description: str = Field(min_length=1, max_length=500)
    status: Literal["not_started", "scheduled", "in_progress", "on_hold", "completed", "cancelled"]
    start: date | None = None
    end: date | None = None

    @model_validator(mode="after")
    def _check(self) -> "PlannedActivity":
        _plain_text(self.description, "description")
        if self.start is not None and self.end is not None and self.end < self.start:
            raise ValueError("end is before start")
        return self


class CarePlan(_Strict):
    """A plan of activities for the patient, for example an exercise programme."""

    id: str = Field(pattern=r"^[A-Za-z0-9._-]{1,64}$")
    title: str = Field(min_length=1, max_length=200)
    status: Literal["active", "on_hold", "completed", "revoked"]
    goal_ids: list[str] = []
    # True only if the DiGA knows the patient put the plan together themselves.
    written_by_patient: bool = False
    activities: list[PlannedActivity] = Field(min_length=1)

    @model_validator(mode="after")
    def _check(self) -> "CarePlan":
        _plain_text(self.title, "title")
        if len(set(self.goal_ids)) != len(self.goal_ids):
            raise ValueError("duplicate goal_ids")
        if self.status in ("completed", "revoked"):
            still_open = [a.description for a in self.activities if a.status in ("not_started", "scheduled", "in_progress")]
            if still_open:
                raise ValueError(f"plan is {self.status} but has open activities: {still_open}")
        return self


class PromScore(_Strict):
    """Total score of one completed instrument. Item answers and wording stay in the DiGA."""

    instrument: Literal["phq9"]
    completed_at: datetime
    score: StrictInt

    @model_validator(mode="after")
    def _check(self) -> "PromScore":
        from ..terminology.instruments import INSTRUMENTS

        if self.completed_at.tzinfo is None:
            raise ValueError("completed_at needs a timezone offset")
        inst = INSTRUMENTS[self.instrument]
        if not inst.min_score <= self.score <= inst.max_score:
            raise ValueError(f"{self.instrument} score {self.score} outside {inst.min_score}..{inst.max_score}")
        return self


class DigaExport(_Strict):
    diga: DigaInfo
    patient: PatientInfo
    period_start: date
    period_end: date
    body_weights: list[BodyWeight] = []
    blood_pressures: list[BloodPressure] = []
    prom_scores: list[PromScore] = []
    diary_entries: list[DiaryEntry] = []
    goals: list[Goal] = []
    care_plans: list[CarePlan] = []

    @model_validator(mode="after")
    def _period_and_uniqueness(self) -> "DigaExport":
        if self.period_end < self.period_start:
            raise ValueError("period_end is before period_start")

        # Everything exported must fall inside the Betrachtungszeitraum, judged by
        # the local date of the recording.
        stamps = [("body_weights", w.measured_at) for w in self.body_weights]
        stamps += [("blood_pressures", b.measured_at) for b in self.blood_pressures]
        stamps += [("prom_scores", p.completed_at) for p in self.prom_scores]
        stamps += [("diary_entries", d.written_at) for d in self.diary_entries]
        outside = [f"{k} {t.isoformat()}" for k, t in stamps if not self.period_start <= t.date() <= self.period_end]
        if outside:
            raise ValueError(f"outside period {self.period_start}..{self.period_end}: {outside}")

        # Resource ids derive from these keys (UUIDv5), so duplicates would collide.
        keys = [w.measured_at for w in self.body_weights]
        if len(set(keys)) != len(keys):
            raise ValueError("duplicate body_weights.measured_at")
        keys = [b.measured_at for b in self.blood_pressures]
        if len(set(keys)) != len(keys):
            raise ValueError("duplicate blood_pressures.measured_at")
        keys = [(p.instrument, p.completed_at) for p in self.prom_scores]
        if len(set(keys)) != len(keys):
            raise ValueError("duplicate prom_scores (instrument, completed_at)")
        keys = [d.written_at for d in self.diary_entries]
        if len(set(keys)) != len(keys):
            raise ValueError("duplicate diary_entries.written_at")

        # Goals and plans may start before the period: they describe what was current in it.
        goal_ids = [g.id for g in self.goals]
        if len(set(goal_ids)) != len(goal_ids):
            raise ValueError("duplicate goals.id")
        plan_ids = [p.id for p in self.care_plans]
        if len(set(plan_ids)) != len(plan_ids):
            raise ValueError("duplicate care_plans.id")
        unknown = sorted({g for p in self.care_plans for g in p.goal_ids} - set(goal_ids))
        if unknown:
            raise ValueError(f"care_plans refer to unknown goals: {unknown}")
        late = [f"goal {g.id}" for g in self.goals if g.start > self.period_end]
        late += [f"plan {p.id}" for p in self.care_plans for a in p.activities if a.start and a.start > self.period_end]
        if late:
            raise ValueError(f"starts after period_end {self.period_end}: {sorted(set(late))}")
        return self
