"""Read gematik's electronic medication list (eML) into the kit's input model.

Source model: de.gematik.epa.medication 1.3.5 (pinned as a reference package,
docs/decisions/0009). The list is a FHIR searchset Bundle of
MedicationStatement, Medication, MedicationRequest, MedicationDispense and
the people and organisations involved.

Data minimisation: only the MedicationStatement and the Medication it refers
to are read. The Patient, Practitioner, Organization, MedicationRequest,
MedicationDispense and Provenance resources in the same bundle are never
touched. Free text that is read (the drug name, the dosage text) can still
contain a name if someone typed one in; the reader does not filter it. The
statement's subject is not read either, so a list of another patient is not
detected.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from pydantic import ValidationError

from ..input.model import Medication
from ..terminology.versions import PZN

Json = dict[str, Any]

# FHIR MedicationStatement.status -> input model. "entered-in-error" is skipped, not mapped.
_STATUS = {
    "active": "active",
    "completed": "completed",
    "intended": "intended",
    "stopped": "stopped",
    "on-hold": "on_hold",
    "unknown": "unknown",
    "not-taken": "not_taken",
}
# The eML statement status value set (epa-medication-statement-status-vs) allows only these
# three; the others are FHIR codes a non-conformant list could still carry.
_EML_STATUS = {"unknown", "intended", "entered-in-error"}
# German designations in de.gematik.epa.medication 1.3.5: epa-medication-statement-status-vs
# for the status, CodeSystem context-code for the origin. KBV's German concept map calls
# "unknown" "Unbekannt", so the note says what the eML meant (docs/gaps.md G19).
_STATUS_DE = {"unknown": "offen", "intended": "geplant"}
_CONTEXT_DE = {"PRESCRIPTION": "Verschreibung", "MANUAL": "Nachtrag", "EMP": "eMP"}
_CONTEXT_URL = "https://gematik.de/fhir/epa-medication/StructureDefinition/context-extension"
# The R5 backport extension that carries the dosage as one line of text.
_RENDERED_DOSAGE = "extension-MedicationStatement.renderedDosageInstruction"
_MAX_DOSAGE = 1000


@dataclass(frozen=True)
class Finding:
    reference: str
    reason: str


@dataclass(frozen=True)
class ImportResult:
    medications: list[Medication] = field(default_factory=list)
    # Entries that were not imported, and why.
    skipped: list[Finding] = field(default_factory=list)
    # Entries that were imported with something left out.
    notes: list[Finding] = field(default_factory=list)


def _date(value: object) -> date | None:
    """The date part of a FHIR date or dateTime; None for a partial date such as 2026-09."""
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _rendered_dosage(statement: Json) -> str | None:
    for ext in statement.get("extension") or []:
        if str(ext.get("url", "")).endswith(_RENDERED_DOSAGE):
            text = ext.get("valueMarkdown") or ext.get("valueString")
            if isinstance(text, str) and text.strip():
                return text.strip()
    for dosage in statement.get("dosage") or []:
        text = dosage.get("text")
        if isinstance(text, str) and text.strip():
            return text.strip()
    return None


def _note(statement: Json, status: str) -> str:
    """Where the entry came from and what its status meant there, in gematik's own German labels."""
    context = next((e.get("valueCode") for e in statement.get("extension") or [] if e.get("url") == _CONTEXT_URL), None)
    parts = ["Aus der ePA-Medikationsliste übernommen."]
    if context in _CONTEXT_DE:
        parts.append(f"Herkunft: {_CONTEXT_DE[context]}.")
    if status in _STATUS_DE:
        parts.append(f"Status dort: {_STATUS_DE[status]}.")
    return " ".join(parts)


def read_medication_list(bundle: Json) -> ImportResult:
    """Parse an eML searchset Bundle. Never raises for a single bad entry: it is reported as skipped."""
    if not isinstance(bundle, dict) or bundle.get("resourceType") != "Bundle":
        raise ValueError("not a FHIR Bundle")

    drugs: dict[str, Json] = {}
    statements: list[Json] = []
    for entry in bundle.get("entry") or []:
        resource = entry.get("resource") or {}
        if resource.get("resourceType") == "Medication":
            if entry.get("fullUrl"):
                drugs[entry["fullUrl"]] = resource
            if resource.get("id"):
                drugs[f"Medication/{resource['id']}"] = resource
        elif resource.get("resourceType") == "MedicationStatement":
            statements.append(resource)

    result = ImportResult()
    if any(link.get("relation") == "next" for link in bundle.get("link") or []):
        # The list operation pages its result (_count, _offset); this reader sees one page only.
        result.notes.append(Finding("Bundle", "the bundle is one page of a longer list; read the other pages too"))
    for statement in statements:
        ref = f"MedicationStatement/{statement.get('id', '?')}"
        status = statement.get("status")
        if status == "entered-in-error":
            result.skipped.append(Finding(ref, "entered in error"))
            continue
        if status not in _STATUS:
            result.skipped.append(Finding(ref, f"status {status!r} is not supported"))
            continue
        if status not in _EML_STATUS:
            result.notes.append(Finding(ref, f"status {status!r} is not an eML status; imported as given"))

        target = str((statement.get("medicationReference") or {}).get("reference") or "")
        # A relative reference, an absolute URL, or the entry's fullUrl; a version suffix is ignored.
        target = target.split("/_history/")[0]
        drug = drugs.get(target) or drugs.get("/".join(target.split("/")[-2:]))
        if drug is None:
            result.skipped.append(Finding(ref, "the medication it refers to is not in the bundle"))
            continue
        code = drug.get("code") or {}
        name = code.get("text")
        if not isinstance(name, str) or not name.strip():
            # No code.text: ingredient-only and compounded medications, and PZN-only entries. The
            # export needs a name, also as the display of a PZN coding (docs/gaps.md G18).
            result.skipped.append(Finding(ref, "the medication has no name"))
            continue

        pzn = next((c.get("code") for c in code.get("coding") or [] if c.get("system") == PZN), None)
        if pzn is not None and not re.fullmatch(r"\d{8}", str(pzn)):
            result.notes.append(Finding(ref, "PZN is not 8 digits; imported by name only"))
            pzn = None

        period = statement.get("effectivePeriod") or {}
        if statement.get("effectiveDateTime") and not period:
            # A point in time is not a start: as "since" it would read as ongoing.
            result.notes.append(Finding(ref, "effectiveDateTime is a point in time, not a period; left out"))
        dates = {}
        for label, value in (("start", period.get("start")), ("end", period.get("end"))):
            dates[label] = _date(value)
            if value and dates[label] is None:
                result.notes.append(Finding(ref, f"{label} is not a full date; left out"))
        asserted = _date(statement.get("dateAsserted"))
        if statement.get("dateAsserted") and asserted is None:
            result.notes.append(Finding(ref, "dateAsserted is not a full date; left out"))
        dosage = _rendered_dosage(statement)
        if dosage is not None and len(dosage) > _MAX_DOSAGE:
            result.notes.append(Finding(ref, f"dosage text longer than {_MAX_DOSAGE} characters; left out"))
            dosage = None
        try:
            result.medications.append(
                Medication(
                    id=str(statement.get("id", "")),
                    name=name.strip(),
                    pzn=pzn,
                    status=_STATUS[status],
                    dosage_text=dosage,
                    since=dates["start"],
                    until=dates["end"],
                    asserted_on=asserted,
                    note=_note(statement, status),
                )
            )
        except ValidationError as exc:
            first = exc.errors()[0]
            where = ".".join(str(p) for p in first["loc"]) or "entry"
            result.skipped.append(Finding(ref, f"{where}: {first['msg']}"))
    return result
