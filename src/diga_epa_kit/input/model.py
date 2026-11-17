"""Input model: the data a DiGA typically holds, independent of FHIR."""

from __future__ import annotations

import unicodedata
from collections.abc import Sequence
from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, StrictFloat, StrictInt, model_validator


class _Strict(BaseModel):
    model_config = {"extra": "forbid", "frozen": True}


class Manufacturer(_Strict):
    name: str
    website: str | None = None


class DigaInfo(_Strict):
    name: str
    ve_id: str = Field(description="DiGA-VE-ID (Verordnungseinheit) from the BfArM directory")
    pzn: str = Field(pattern=r"^\d{8}$")
    version: str | None = Field(
        default=None,
        pattern=r"^[0-9A-Za-z][0-9A-Za-z.+_-]{0,39}$",
        description="Software version of the app that produced the data. Letters, digits and . + _ - only; "
        "write a build number as 2.4.1+57",
    )
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
    def _tz_aware(self) -> BodyWeight:
        # FHIR dateTime with a time part must carry a timezone offset.
        if self.measured_at.tzinfo is None:
            raise ValueError("measured_at needs a timezone offset")
        return self


class BodyHeight(_Strict):
    """Body height in cm. Usually typed in once, often before the export period."""

    measured_at: datetime
    cm: float = Field(gt=30, lt=280)

    @model_validator(mode="after")
    def _tz_aware(self) -> BodyHeight:
        if self.measured_at.tzinfo is None:
            raise ValueError("measured_at needs a timezone offset")
        return self


class _Measured(_Strict):
    measured_at: datetime

    @model_validator(mode="after")
    def _tz_aware(self) -> _Measured:
        if self.measured_at.tzinfo is None:
            raise ValueError("measured_at needs a timezone offset")
        return self


# The bounds below are plausibility limits that catch unit and typing mistakes,
# not clinical limits.
class HeartRate(_Measured):
    """Beats per minute."""

    bpm: StrictInt = Field(ge=20, le=300)


class BodyTemperature(_Measured):
    """Degrees Celsius; the input does not say where on the body it was taken."""

    celsius: StrictFloat | StrictInt = Field(ge=25, le=45)


class OxygenSaturation(_Measured):
    """Peripheral oxygen saturation in percent, from a pulse oximeter (the profile fixes that method)."""

    percent: StrictInt = Field(
        ge=50,
        le=100,
        description="Pulse-oximeter readings only: the export states that method for every value",
    )


class RespiratoryRate(_Measured):
    """Breaths per minute."""

    per_minute: StrictInt = Field(ge=4, le=80)


class Glucose(_Measured):
    """One glucose reading, exported in the unit the app holds (never converted).

    ``specimen`` says what was measured: ``blood`` (a finger-prick meter) or
    ``interstitial_fluid`` (a sensor worn on the skin). Every sensor reading is exported
    with continuous glucose monitoring as its method. ``context`` applies to blood
    readings only and says when the reading was taken. ``outside_measuring_range`` marks a reading
    the device showed as LO or HI; ``value`` is then the device's measuring limit.
    """

    value: StrictFloat | StrictInt
    unit: Literal["mg/dL", "mmol/L"] = Field(
        description="Unit of the value. Any number from 10 to 56 is plausible in both units, "
        "so a wrong unit in that range cannot be detected"
    )
    specimen: Literal["blood", "interstitial_fluid"] = Field(
        description="blood: finger-prick meter. interstitial_fluid: glucose sensor worn on the skin; "
        "exported with continuous glucose monitoring (CGM) as the method"
    )
    context: Literal["fasting", "before_lunch", "before_supper", "before_bed", "after_meal", "random"] | None = Field(
        default=None,
        description="Blood readings only. fasting; before_lunch, before_supper and before_bed: taken "
        "before that meal or before going to bed; after_meal; random: at no particular time",
    )
    outside_measuring_range: Literal["below", "above"] | None = Field(
        default=None,
        description="Set when the device showed LO or HI instead of a number: the reading lay outside what "
        "the device can measure. This is not the patient's target range. value is then the device's "
        "measuring limit, the lowest (below) or highest (above) number it still shows, with at most one "
        "decimal. A lower limit must be at most 100 mg/dL or 5.6 mmol/L, an upper limit at least 200 mg/dL "
        "or 11.1 mmol/L. Exported as below or above the limit, which a receiver must not read as the value",
    )

    @model_validator(mode="after")
    def _plausible(self) -> Glucose:
        # Plausibility limits per unit. They overlap from 10 to 56, so a wrong unit is only
        # caught outside that window (docs/mapping.md). NaN fails the comparison too.
        low, high = (10, 1000) if self.unit == "mg/dL" else (0.5, 56)
        if not low <= self.value <= high:
            raise ValueError(f"glucose {self.value} {self.unit} outside {low}..{high}")
        if self.specimen == "interstitial_fluid" and self.context is not None:
            raise ValueError("context applies to blood readings only")
        # A lower measuring limit lies at or below normal fasting glucose, an upper one well
        # above it. This catches a swapped direction and a limit given in the other unit.
        lower_at_most, upper_at_least = (100, 200) if self.unit == "mg/dL" else (5.6, 11.1)
        if self.outside_measuring_range == "below" and self.value > lower_at_most:
            raise ValueError(
                f"a lower measuring limit of {self.value} {self.unit} is implausible (at most {lower_at_most})"
            )
        if self.outside_measuring_range == "above" and self.value < upper_at_least:
            raise ValueError(
                f"an upper measuring limit of {self.value} {self.unit} is implausible (at least {upper_at_least})"
            )
        if self.outside_measuring_range and round(self.value, 1) != self.value:
            # Rounding "<2.24" to "<2.2" would claim more than the device said.
            raise ValueError("a measuring limit takes at most one decimal")
        return self


class BloodPressure(_Strict):
    """One reading in mmHg. The bounds are plausibility limits, not clinical ones."""

    measured_at: datetime
    systolic: StrictInt = Field(ge=40, le=300)
    diastolic: StrictInt = Field(ge=20, le=200)

    @model_validator(mode="after")
    def _check(self) -> BloodPressure:
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
    def _check(self) -> DiaryEntry:
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


class Medication(_Strict):
    """A medication the patient takes or was prescribed, for example read from the ePA medication list.

    Only what the export needs: no prescriber, no pharmacy, no insurance number.
    """

    # A stable key, for example the id of the entry in the ePA medication list. It is not exported.
    id: str = Field(pattern=r"^[A-Za-z0-9._-]{1,64}$")
    name: str = Field(min_length=1, max_length=300, description="Drug name as the source states it")
    pzn: str | None = Field(default=None, pattern=r"^\d{8}$", description="Pharmazentralnummer, 8 digits")
    # No default: a missing status must not turn into a statement about the patient.
    status: Literal["active", "completed", "intended", "stopped", "on_hold", "unknown", "not_taken"]
    dosage_text: str | None = Field(default=None, min_length=1, max_length=1000)
    since: date | None = None
    until: date | None = None
    asserted_on: date | None = Field(default=None, description="When the source recorded the entry")
    note: str | None = Field(
        default=None,
        min_length=1,
        max_length=500,
        description="Free text exported as the statement's note, for example where the entry came from. "
        "No names of people",
    )

    @model_validator(mode="after")
    def _check(self) -> Medication:
        _plain_text(self.name, "name")
        if self.dosage_text is not None:
            _plain_text(self.dosage_text, "dosage_text")
        if self.note is not None:
            _plain_text(self.note, "note")
        if self.since is not None and self.until is not None and self.until < self.since:
            raise ValueError("until is before since")
        return self


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
    def _check(self) -> Goal:
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
    def _check(self) -> PlannedActivity:
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
    def _check(self) -> CarePlan:
        _plain_text(self.title, "title")
        if len(set(self.goal_ids)) != len(self.goal_ids):
            raise ValueError("duplicate goal_ids")
        if self.status in ("completed", "revoked"):
            still_open = [
                a.description for a in self.activities if a.status in ("not_started", "scheduled", "in_progress")
            ]
            if still_open:
                raise ValueError(f"plan is {self.status} but has open activities: {still_open}")
        return self


class PromScore(_Strict):
    """Total score of one completed instrument. Item answers and wording stay in the DiGA."""

    instrument: Literal["phq9", "gad7", "pain_nrs", "odi"]
    completed_at: datetime
    score: StrictInt

    @model_validator(mode="after")
    def _check(self) -> PromScore:
        from ..terminology.instruments import INSTRUMENTS

        if self.completed_at.tzinfo is None:
            raise ValueError("completed_at needs a timezone offset")
        inst = INSTRUMENTS[self.instrument]
        if not inst.min_score <= self.score <= inst.max_score:
            raise ValueError(f"{self.instrument} score {self.score} outside {inst.min_score}..{inst.max_score}")
        return self


class BodyMassIndex(_Strict):
    """A BMI the DiGA calculated. The bounds are plausibility limits, not clinical ones.

    ``measured_at`` is the time of the weight reading the BMI is based on, not the
    time the app did the arithmetic.
    """

    measured_at: datetime
    kg_m2: float = Field(ge=5, le=150)

    @model_validator(mode="after")
    def _tz_aware(self) -> BodyMassIndex:
        if self.measured_at.tzinfo is None:
            raise ValueError("measured_at needs a timezone offset")
        return self


class DailySteps(_Strict):
    """Step count of one calendar day, as the patient's phone or wearable reported it.

    Leave out days without data: 0 is exported as a real count of zero steps.
    """

    day: date
    steps: StrictInt = Field(ge=0, le=200_000)


class DigaExport(_Strict):
    diga: DigaInfo
    patient: PatientInfo
    period_start: date
    period_end: date
    body_weights: list[BodyWeight] = []
    body_heights: list[BodyHeight] = []
    blood_pressures: list[BloodPressure] = []
    heart_rates: list[HeartRate] = []
    body_temperatures: list[BodyTemperature] = []
    oxygen_saturations: list[OxygenSaturation] = []
    respiratory_rates: list[RespiratoryRate] = []
    glucose_readings: list[Glucose] = []
    body_mass_indices: list[BodyMassIndex] = []
    daily_steps: list[DailySteps] = []
    prom_scores: list[PromScore] = []
    diary_entries: list[DiaryEntry] = []
    goals: list[Goal] = []
    care_plans: list[CarePlan] = []
    medications: list[Medication] = []

    @model_validator(mode="after")
    def _period_and_uniqueness(self) -> DigaExport:
        if self.period_end < self.period_start:
            raise ValueError("period_end is before period_start")

        # Every dated measurement except body height must fall inside the
        # Betrachtungszeitraum, judged by the local date of the recording.
        stamps = [("body_weights", w.measured_at) for w in self.body_weights]
        stamps += [("blood_pressures", b.measured_at) for b in self.blood_pressures]
        simple: dict[str, Sequence[_Measured]] = {
            "heart_rates": self.heart_rates,
            "body_temperatures": self.body_temperatures,
            "oxygen_saturations": self.oxygen_saturations,
            "respiratory_rates": self.respiratory_rates,
        }
        for name, readings in simple.items():
            stamps += [(name, r.measured_at) for r in readings]
            if len({r.measured_at for r in readings}) != len(readings):
                raise ValueError(f"duplicate {name}.measured_at")
        stamps += [("glucose_readings", g.measured_at) for g in self.glucose_readings]
        # A meter and a sensor can report in the same minute, so the specimen is part of the key.
        if len({(g.specimen, g.measured_at) for g in self.glucose_readings}) != len(self.glucose_readings):
            raise ValueError("duplicate glucose_readings (specimen, measured_at)")
        stamps += [("body_mass_indices", b.measured_at) for b in self.body_mass_indices]
        stamps += [("prom_scores", p.completed_at) for p in self.prom_scores]
        stamps += [("diary_entries", d.written_at) for d in self.diary_entries]
        outside = [f"{k} {t.isoformat()}" for k, t in stamps if not self.period_start <= t.date() <= self.period_end]
        outside += [
            f"daily_steps {s.day.isoformat()}"
            for s in self.daily_steps
            if not self.period_start <= s.day <= self.period_end
        ]
        if outside:
            raise ValueError(f"outside period {self.period_start}..{self.period_end}: {outside}")

        # Resource ids derive from these keys (UUIDv5), so duplicates would collide.
        keys: list[object] = [w.measured_at for w in self.body_weights]
        if len(set(keys)) != len(keys):
            raise ValueError("duplicate body_weights.measured_at")
        keys = [h.measured_at for h in self.body_heights]
        if len(set(keys)) != len(keys):
            raise ValueError("duplicate body_heights.measured_at")
        keys = [b.measured_at for b in self.blood_pressures]
        if len(set(keys)) != len(keys):
            raise ValueError("duplicate blood_pressures.measured_at")
        keys = [b.measured_at for b in self.body_mass_indices]
        if len(set(keys)) != len(keys):
            raise ValueError("duplicate body_mass_indices.measured_at")
        keys = [s.day for s in self.daily_steps]
        if len(set(keys)) != len(keys):
            raise ValueError("duplicate daily_steps.day")
        keys = [(p.instrument, p.completed_at) for p in self.prom_scores]
        if len(set(keys)) != len(keys):
            raise ValueError("duplicate prom_scores (instrument, completed_at)")
        keys = [d.written_at for d in self.diary_entries]
        if len(set(keys)) != len(keys):
            raise ValueError("duplicate diary_entries.written_at")

        # Goals and plans may start before the period: they describe what was current in it.
        medication_ids = [m.id for m in self.medications]
        if len(set(medication_ids)) != len(medication_ids):
            raise ValueError("duplicate medications.id")
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
        # Like a goal, a medication may be older than the period: it is what was current in it.
        late += [f"medication {m.id}" for m in self.medications if m.since and m.since > self.period_end]
        # A height is usually entered once at the start of use, so it may predate the
        # period: it is the height that was current in it.
        late += [
            f"body_heights {h.measured_at.isoformat()}"
            for h in self.body_heights
            if h.measured_at.date() > self.period_end
        ]
        late += [f"plan {p.id}" for p in self.care_plans for a in p.activities if a.start and a.start > self.period_end]
        if late:
            raise ValueError(f"starts after period_end {self.period_end}: {sorted(set(late))}")
        return self
