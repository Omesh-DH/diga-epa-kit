"""Vital signs and body measurements (section Befunde und Ergebnisse > Vitalzeichen)."""

from __future__ import annotations

from datetime import datetime

from ..input.model import BloodPressure, BodyWeight
from ..terminology.versions import LOINC, OBS_CATEGORY, SNOMED, UCUM, VersionPack
from .common import Json, meta, ri_identifier, urn

_WEIGHT_METHOD = {
    "measured": ("363808001", "Measured body weight (observable entity)"),
    "self_reported": ("786458005", "Self reported usual body weight (observable entity)"),
}


def body_weight(pack: VersionPack, uuid: str, patient_uuid: str, obs: BodyWeight, now: datetime) -> Json:
    method_code, method_display = _WEIGHT_METHOD[obs.method]
    return {
        "resourceType": "Observation",
        "id": uuid,
        "meta": meta(pack, "body_weight", now),
        "identifier": [ri_identifier(pack, uuid)],
        "status": "final",
        "category": [{"coding": [{"system": OBS_CATEGORY, "code": "vital-signs"}]}],
        "code": {
            "coding": [
                {"system": LOINC, "version": pack.loinc_version, "code": "29463-7", "display": "Body weight"},
                {
                    "system": SNOMED,
                    "version": pack.snomed_version,
                    "code": "27113001",
                    "display": "Body weight (observable entity)",
                },
            ]
        },
        "subject": {"reference": urn(patient_uuid)},
        "effectiveDateTime": obs.measured_at.isoformat(),
        # Home measurements: the patient is the performer, whether scale-synced or typed in.
        "performer": [{"reference": urn(patient_uuid)}],
        "valueQuantity": {"value": round(obs.kg, 2), "unit": "kg", "system": UCUM, "code": "kg"},
        "method": {
            "coding": [
                {"system": SNOMED, "version": pack.snomed_version, "code": method_code, "display": method_display}
            ]
        },
    }


def _bp_component(pack: VersionPack, loinc: tuple[str, str], snomed: tuple[str, str], value: int) -> Json:
    return {
        "code": {
            "coding": [
                {"system": LOINC, "version": pack.loinc_version, "code": loinc[0], "display": loinc[1]},
                {"system": SNOMED, "version": pack.snomed_version, "code": snomed[0], "display": snomed[1]},
            ]
        },
        # Unit text "mm Hg" is the kbv.basis pattern; the UCUM code is mm[Hg].
        "valueQuantity": {"value": value, "unit": "mm Hg", "system": UCUM, "code": "mm[Hg]"},
    }


def blood_pressure(pack: VersionPack, uuid: str, patient_uuid: str, obs: BloodPressure, now: datetime) -> Json:
    # Codes and displays: de.basisprofil.r4 VitalSignDE_Blutdruck (LOINC codes) and
    # kbv.basis KBV_PR_Base_Observation_Blood_Pressure (LOINC displays, SNOMED codings).
    return {
        "resourceType": "Observation",
        "id": uuid,
        "meta": meta(pack, "blood_pressure", now),
        "identifier": [ri_identifier(pack, uuid)],
        "status": "final",
        "category": [{"coding": [{"system": OBS_CATEGORY, "code": "vital-signs"}]}],
        "code": {
            "coding": [
                {
                    "system": LOINC,
                    "version": pack.loinc_version,
                    "code": "85354-9",
                    "display": "Blood pressure panel with all children optional",
                },
                {
                    "system": SNOMED,
                    "version": pack.snomed_version,
                    "code": "75367002",
                    "display": "Blood pressure (observable entity)",
                },
            ]
        },
        "subject": {"reference": urn(patient_uuid)},
        "effectiveDateTime": obs.measured_at.isoformat(),
        # Home measurements: the patient is the performer, whether cuff-synced or typed in.
        "performer": [{"reference": urn(patient_uuid)}],
        # No Observation.value: the base profile prohibits it, the reading lives in the components.
        "component": [
            _bp_component(
                pack,
                ("8480-6", "Systolic blood pressure"),
                ("271649006", "Systolic blood pressure (observable entity)"),
                obs.systolic,
            ),
            _bp_component(
                pack,
                ("8462-4", "Diastolic blood pressure"),
                ("271650006", "Diastolic blood pressure (observable entity)"),
                obs.diastolic,
            ),
        ],
    }
