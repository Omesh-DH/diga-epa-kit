"""Vital signs and body measurements (section Befunde und Ergebnisse > Vitalzeichen)."""

from __future__ import annotations

from datetime import datetime

from ..input.model import BodyWeight
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
