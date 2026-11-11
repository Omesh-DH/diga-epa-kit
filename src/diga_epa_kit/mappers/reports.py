"""Patient-written reports (section Patientenberichte)."""

from __future__ import annotations

from datetime import datetime

from ..input.model import DiaryEntry
from ..terminology.versions import LOINC, VersionPack
from .common import Json, meta, ri_identifier, urn


def diary_entry(pack: VersionPack, uuid: str, patient_uuid: str, entry: DiaryEntry, now: datetime) -> Json:
    return {
        "resourceType": "Observation",
        "id": uuid,
        "meta": meta(pack, "diary_entry", now),
        "identifier": [ri_identifier(pack, uuid)],
        "status": "final",
        # No category, method or device: the profile prohibits them here.
        # Code pattern of KBV_PR_MIO_DIGA_Observation_Diary_Entry (Observation.code).
        "code": {
            "coding": [
                {"system": LOINC, "version": pack.loinc_version, "code": "51855-5", "display": "Patient Note"}
            ]
        },
        "subject": {"reference": urn(patient_uuid)},
        "effectiveDateTime": entry.written_at.isoformat(),
        "performer": [{"reference": urn(patient_uuid)}],
        "valueString": entry.text,
    }
