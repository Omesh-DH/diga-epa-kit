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
_SECTION_MEDICATION = ("Medikation", "721912009", "Medication summary document (record artifact)")
_SECTION_ASSESSMENTS = ("Beurteilungen", "424836000", "Assessment section (record artifact)")
# KBV's own section codes (KBV_CS_MIO_DIGA_Section_Codes in kbv.mio.diga), versioned with the package.
_KBV_SECTION_CODES = "https://fhir.kbv.de/CodeSystem/KBV_CS_MIO_DIGA_Section_Codes"
_SECTION_GOALS = ("Ziele", "SectionZiele", "Bereich Ziele")
_SECTION_PATIENT_REPORTS = ("Patientenberichte", "SectionPatientenberichte", "Bereich Patientenberichte")


def _snomed_section(pack: VersionPack, spec: tuple[str, str, str], **content: Any) -> Json:
    title, code, display = spec
    return {
        "title": title,
        "code": {"coding": [{"system": SNOMED, "version": pack.snomed_version, "code": code, "display": display}]},
        **content,
    }


def _kbv_section(pack: VersionPack, spec: tuple[str, str, str], **content: Any) -> Json:
    title, code, display = spec
    return {
        "title": title,
        "code": {
            "coding": [
                {"system": _KBV_SECTION_CODES, "version": pack.section_codes_version, "code": code, "display": display}
            ]
        },
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
    results: Sequence[str] = (),
    vital_signs: Sequence[str] = (),
    medications: Sequence[str] = (),
    assessments: Sequence[str] = (),
    goals: Sequence[str] = (),
    patient_reports: Sequence[str] = (),
) -> Json:
    # Emitted in the order the profile declares its section slices.
    sections: list[Json] = []
    if results or vital_signs:
        # Free results are entries of the results section itself; the specific
        # vital-sign profiles sit in its Vitalzeichen subsection.
        content: dict[str, Any] = {}
        if results:
            content["entry"] = _entries(results)
        if vital_signs:
            content["section"] = [_snomed_section(pack, _SECTION_VITALS, entry=_entries(vital_signs))]
        sections.append(_snomed_section(pack, _SECTION_RESULTS, **content))
    if medications:
        # Only the statements are entries; each refers to its Medication.
        sections.append(_snomed_section(pack, _SECTION_MEDICATION, entry=_entries(medications)))
    if assessments:
        sections.append(_snomed_section(pack, _SECTION_ASSESSMENTS, entry=_entries(assessments)))
    if goals:
        sections.append(_kbv_section(pack, _SECTION_GOALS, entry=_entries(goals)))
    if patient_reports:
        sections.append(_kbv_section(pack, _SECTION_PATIENT_REPORTS, entry=_entries(patient_reports)))

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
