"""PROM total scores as Observation_Score_or_Assessment_by_Scale (section Beurteilungen)."""

from __future__ import annotations

from datetime import datetime

from ..input.model import PromScore
from ..terminology.instruments import Instrument
from ..terminology.versions import OBS_CATEGORY, UCUM, VersionPack
from .common import Json, loinc, meta, ri_identifier, urn


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
        # Scale bounds, not a normal range. The profile prohibits referenceRange.text.
        "referenceRange": [{"low": _score_qty(inst.min_score), "high": _score_qty(inst.max_score)}],
        "device": {"reference": urn(device_uuid)},
    }
