"""Other results (section Befunde und Ergebnisse, directly, not under Vitalzeichen).

KBV_PR_MIO_DIGA_Observation_Free constrains almost nothing: no code pattern, no
identifier slice, no must-support. What is emitted here is therefore the kit's
choice, kept close to the specific vital-sign mappers (docs/mapping.md).
"""

from __future__ import annotations

from datetime import datetime

from ..input.model import BodyMassIndex, DailySteps
from ..terminology.versions import LOINC, OBS_CATEGORY, UCUM, VersionPack
from .common import Json, meta, urn


def body_mass_index(
    pack: VersionPack, uuid: str, patient_uuid: str, device_uuid: str, obs: BodyMassIndex, now: datetime
) -> Json:
    return {
        "resourceType": "Observation",
        "id": uuid,
        "meta": meta(pack, "observation_free", now),
        "status": "final",
        # FHIR R4 treats 39156-5 as a vital sign: the validator applies the core bmi
        # profile, which requires this category, a subject, a time and kg/m2.
        "category": [{"coding": [{"system": OBS_CATEGORY, "code": "vital-signs"}]}],
        "code": {
            "coding": [
                # Code, display and unit as in de.basisprofil.r4 examples/Example-observation-bmi.json
                # and loinc.org/39156-5 (read 2026-11-12); 2.72 name not confirmed (docs/gaps.md G9).
                {
                    "system": LOINC,
                    "version": pack.loinc_version,
                    "code": "39156-5",
                    "display": "Body mass index (BMI) [Ratio]",
                }
            ]
        },
        "subject": {"reference": urn(patient_uuid)},
        # The time of the underlying weight reading, not of the calculation.
        "effectiveDateTime": obs.measured_at.isoformat(),
        "valueQuantity": {"value": round(obs.kg_m2, 1), "unit": "kg/m2", "system": UCUM, "code": "kg/m2"},
        # Calculated by the app, not measured by the patient: no performer.
        "device": {"reference": urn(device_uuid)},
    }


def daily_steps(pack: VersionPack, uuid: str, patient_uuid: str, obs: DailySteps, now: datetime) -> Json:
    return {
        "resourceType": "Observation",
        "id": uuid,
        "meta": meta(pack, "observation_free", now),
        "status": "final",
        "category": [{"coding": [{"system": OBS_CATEGORY, "code": "activity"}]}],
        "code": {
            "coding": [
                # Long common name from loinc.org/41950-7 (read 2026-11-12), unchanged since 2.48.
                {
                    "system": LOINC,
                    "version": pack.loinc_version,
                    "code": "41950-7",
                    "display": "Number of steps in 24 hour Measured",
                }
            ]
        },
        "subject": {"reference": urn(patient_uuid)},
        # A calendar day without a time: the count belongs to the whole day.
        "effectiveDateTime": obs.day.isoformat(),
        # Counted by the patient's phone or wearable, which the input does not identify.
        "performer": [{"reference": urn(patient_uuid)}],
        # UCUM code as in the example units on loinc.org/41950-7 (read 2026-11-12).
        "valueQuantity": {"value": obs.steps, "unit": "Schritte/24 h", "system": UCUM, "code": "{#}/(24.h)"},
    }
