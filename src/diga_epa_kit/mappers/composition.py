"""The Composition: document header and the section slices that list every entry."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime
from typing import Any

from ..terminology.versions import LOINC, SNOMED, VersionPack
from .common import Json, meta, urn

# Section codings are fixed by the profile; keyed by the profile's slice names.
_SECTION_RESULTS = ("Befunde und Ergebnisse", "423100009", "Results section (record artifact)")
_SECTION_VITALS = ("Vitalzeichen und Körpermaße", "1184593002", "Vital sign document section (record artifact)")
_SECTION_ASSESSMENTS = ("Beurteilungen", "424836000", "Assessment section (record artifact)")


def _snomed_section(pack: VersionPack, spec: tuple[str, str, str], **content: Any) -> Json:
    title, code, display = spec
    return {
        "title": title,
        "code": {"coding": [{"system": SNOMED, "version": pack.snomed_version, "code": code, "display": display}]},
        **content,
    }


def _kbv_section(pack: VersionPack, title: str, code: str, display: str, **content: Any) -> Json:
    system = "https://fhir.kbv.de/CodeSystem/KBV_CS_MIO_DIGA_Section_Codes"
    return {
        "title": title,
        "code": {"coding": [{"system": system, "version": pack.version, "code": code, "display": display}]},
        **content,
    }


def _entries(uuids: Sequence[str]) -> list[Json]:
    return [{"reference": urn(u)} for u in uuids]


def composition(
    pack: VersionPack,
    uuid: str,
    patient_uuid: str,
    device_uuid: str,
    period: tuple[date, date],
    now: datetime,
    *,
    vital_signs: Sequence[str] = (),
    questionnaires: Sequence[str] = (),
    assessments: Sequence[str] = (),
) -> Json:
    # Emitted in the order the profile declares its section slices.
    sections: list[Json] = []
    if questionnaires:
        sections.append(
            _kbv_section(pack, "Fragebögen", "SectionFrageboegen", "Bereich Fragebögen", entry=_entries(questionnaires))
        )
    if vital_signs:
        vitals = _snomed_section(pack, _SECTION_VITALS, entry=_entries(vital_signs))
        sections.append(_snomed_section(pack, _SECTION_RESULTS, section=[vitals]))
    if assessments:
        sections.append(_snomed_section(pack, _SECTION_ASSESSMENTS, entry=_entries(assessments)))

    res: Json = {
        "resourceType": "Composition",
        "id": uuid,
        "meta": meta(pack, "composition", now),
        "extension": [
            {
                "url": "https://fhir.kbv.de/StructureDefinition/KBV_EX_MIO_DIGA_Betrachtungszeitraum",
                "valuePeriod": {"start": period[0].isoformat(), "end": period[1].isoformat()},
            }
        ],
        "status": "final",
        "type": {
            "coding": [
                {
                    "system": LOINC,
                    "version": pack.loinc_version,
                    "code": "53576-5",
                    # Fixed by the profile pattern although current LOINC rejects it (docs/gaps.md G1).
                    "display": "Personal health monitoring report Document",
                }
            ]
        },
        "subject": {"reference": urn(patient_uuid)},
        "date": now.isoformat(),
        "author": [{"reference": urn(device_uuid)}],
        "title": "DiGA-Export",
    }
    if sections:  # FHIR JSON forbids empty arrays
        res["section"] = sections
    return res
