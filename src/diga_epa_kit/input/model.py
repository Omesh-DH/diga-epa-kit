"""Input model: the data a DiGA typically holds, independent of FHIR."""

from __future__ import annotations

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
    prom_scores: list[PromScore] = []

    @model_validator(mode="after")
    def _period_and_uniqueness(self) -> "DigaExport":
        if self.period_end < self.period_start:
            raise ValueError("period_end is before period_start")

        # Everything exported must fall inside the Betrachtungszeitraum, judged by
        # the local date of the recording.
        stamps = [("body_weights", w.measured_at) for w in self.body_weights]
        stamps += [("prom_scores", p.completed_at) for p in self.prom_scores]
        outside = [f"{k} {t.isoformat()}" for k, t in stamps if not self.period_start <= t.date() <= self.period_end]
        if outside:
            raise ValueError(f"outside period {self.period_start}..{self.period_end}: {outside}")

        # Resource ids derive from these keys (UUIDv5), so duplicates would collide.
        keys = [w.measured_at for w in self.body_weights]
        if len(set(keys)) != len(keys):
            raise ValueError("duplicate body_weights.measured_at")
        keys = [(p.instrument, p.completed_at) for p in self.prom_scores]
        if len(set(keys)) != len(keys):
            raise ValueError("duplicate prom_scores (instrument, completed_at)")
        return self
