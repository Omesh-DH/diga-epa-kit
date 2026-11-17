"""Medication (section Medikation): what the patient takes or was prescribed.

Two resources per entry: the drug (Medication) and the statement that the
patient has it (MedicationStatement_Medication_Information). Only the
statement is a section entry; it refers to the drug.
"""

from __future__ import annotations

from datetime import datetime

from ..input.model import Medication
from ..terminology.versions import PZN, VersionPack
from .common import Json, meta, ri_identifier, urn

# FHIR MedicationStatement.status writes two codes with a hyphen.
_STATUS = {"on_hold": "on-hold", "not_taken": "not-taken"}


def medication(pack: VersionPack, uuid: str, med: Medication, now: datetime) -> Json:
    code: Json = {}
    if med.pzn:
        # The pznCode slice requires a version and a display. The packages do not say which
        # version; the kit uses the one the code system definition states (docs/gaps.md G18).
        # The display is the drug name: PZN names come from a list the kit does not have.
        code["coding"] = [{"system": PZN, "version": pack.pzn_version, "code": med.pzn, "display": med.name}]
    code["text"] = med.name
    return {
        "resourceType": "Medication",
        "id": uuid,
        "meta": meta(pack, "medication", now),
        "identifier": [ri_identifier(pack, uuid)],
        # No status: the profile prohibits Medication.status.
        "code": code,
    }


def medication_statement(
    pack: VersionPack, uuid: str, patient_uuid: str, medication_uuid: str, med: Medication, now: datetime
) -> Json:
    res: Json = {
        "resourceType": "MedicationStatement",
        "id": uuid,
        "meta": meta(pack, "medication_statement", now),
        "identifier": [ri_identifier(pack, uuid)],
        "status": _STATUS.get(med.status, med.status),
        "medicationReference": {"reference": urn(medication_uuid)},
        "subject": {"reference": urn(patient_uuid)},
    }
    if med.since or med.until:
        period: Json = {}
        if med.since:
            period["start"] = med.since.isoformat()
        if med.until:
            period["end"] = med.until.isoformat()
        res["effectivePeriod"] = period
    if med.asserted_on:
        res["dateAsserted"] = med.asserted_on.isoformat()
    # Required, and only a person can be named. For data from the patient's own record the kit
    # names the patient; the prescriber or pharmacy is not exported (docs/gaps.md G17).
    res["informationSource"] = {"reference": urn(patient_uuid)}
    if med.note:
        # note.author and note.time are prohibited; the text is all the profile allows.
        res["note"] = [{"text": med.note}]
    if med.dosage_text:
        res["dosage"] = [{"text": med.dosage_text}]
    return res
