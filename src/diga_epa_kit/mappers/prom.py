"""PROM total scores as Observation_Score_or_Assessment_by_Scale (section Beurteilungen)."""

from __future__ import annotations

from datetime import datetime

from ..input.model import PromScore
from ..terminology.instruments import Instrument
from ..terminology.versions import OBS_CATEGORY, UCUM, VersionPack
from .common import Json, loinc, meta, ri_identifier, urn


# German, like the section titles the profile fixes.
_SCALE_RANGE = "Wertebereich der Skala"


def _score_qty(value: int) -> Json:
    return {"value": value, "unit": "{score}", "system": UCUM, "code": "{score}"}


def score(
    pack: VersionPack,
    uuid: str,
    patient_uuid: str,
    device_uuid: str,
    inst: Instrument,
    entry: PromScore,
    now: datetime,
) -> Json:
    return {
        "resourceType": "Observation",
        "id": uuid,
        "meta": meta(pack, "score", now),
        "identifier": [ri_identifier(pack, uuid)],
        "status": "final",
        "category": [{"coding": [{"system": OBS_CATEGORY, "version": "4.0.1", "code": "survey", "display": "Survey"}]}],
        "code": {"coding": [loinc(pack, inst.total_score)]},
        "subject": {"reference": urn(patient_uuid)},
        "effectiveDateTime": entry.completed_at.isoformat(),
        "performer": [{"reference": urn(patient_uuid)}],
        "valueQuantity": _score_qty(entry.score),
        # The scale's bounds, as in KBV's own example bundle, not a normal range. The profile
        # prohibits referenceRange.text, so type.text says what the range is; no coded
        # range type means "possible values" (docs/mapping.md).
        "referenceRange": [
            {
                "low": _score_qty(inst.min_score),
                "high": _score_qty(inst.max_score),
                "type": {"text": _SCALE_RANGE},
            }
        ],
        "device": {"reference": urn(device_uuid)},
    }
