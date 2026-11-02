"""PROMs: Questionnaire + QuestionnaireResponse (Fragebögen) and score Observation (Beurteilungen)."""

from __future__ import annotations

from datetime import datetime

from ..input.model import PromResponse
from ..terminology.instruments import Instrument
from ..terminology.versions import OBS_CATEGORY, UCUM, VersionPack
from .common import Json, loinc, meta, ri_identifier, urn


def _score_qty(value: int) -> Json:
    return {"value": value, "unit": "{score}", "system": UCUM, "code": "{score}"}


def questionnaire(pack: VersionPack, uuid: str, inst: Instrument, now: datetime) -> Json:
    # ques-1 in the profile: exactly one of title / code, so the panel code identifies it.
    return {
        "resourceType": "Questionnaire",
        "id": uuid,
        "meta": meta(pack, "questionnaire", now),
        "language": inst.language,
        "url": inst.url,
        "identifier": [ri_identifier(pack, uuid)],
        "status": "active",
        "code": [loinc(pack, inst.panel)],
        "item": [
            {
                "linkId": item.link_id,
                "code": [loinc(pack, item.code)],
                "text": item.code.display,
                "type": "choice",
                "required": True,
                "answerOption": [{"valueCoding": loinc(pack, a.code)} for a in inst.answers],
            }
            for item in inst.items
        ],
    }


def questionnaire_response(
    pack: VersionPack, uuid: str, patient_uuid: str, inst: Instrument, resp: PromResponse, now: datetime
) -> Json:
    return {
        "resourceType": "QuestionnaireResponse",
        "id": uuid,
        "meta": meta(pack, "questionnaire_response", now),
        "identifier": ri_identifier(pack, uuid),
        "questionnaire": inst.url,
        "status": "completed",
        "subject": {"reference": urn(patient_uuid)},
        "authored": resp.completed_at.isoformat(),
        "author": {"reference": urn(patient_uuid)},
        "item": [
            {
                "linkId": item.link_id,
                "text": item.code.display,
                "answer": [{"valueCoding": loinc(pack, inst.answer(resp.answers[item.link_id]).code)}],
            }
            for item in inst.items
        ],
    }


def score(
    pack: VersionPack,
    uuid: str,
    patient_uuid: str,
    device_uuid: str,
    response_uuid: str,
    inst: Instrument,
    resp: PromResponse,
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
        "effectiveDateTime": resp.completed_at.isoformat(),
        "performer": [{"reference": urn(patient_uuid)}],
        "valueQuantity": _score_qty(resp.total),
        # Scale bounds, not a normal range. The profile prohibits referenceRange.text.
        "referenceRange": [{"low": _score_qty(0), "high": _score_qty(inst.max_score)}],
        "device": {"reference": urn(device_uuid)},
        "derivedFrom": [{"reference": urn(response_uuid)}],
    }
