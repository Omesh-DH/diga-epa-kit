"""Bridge between the try-it page and the kit. Runs inside the browser (Pyodide) and in tests.

Every function takes and returns JSON text, so the page needs no Python objects.
"""

from __future__ import annotations

import json
from collections import Counter
from typing import Any

from pydantic import ValidationError

from diga_epa_kit import DigaExport, build_bundle, check_bundle
from diga_epa_kit.epa_import import read_medication_list

Json = dict[str, Any]
_PROFILE_PREFIX = "KBV_PR_MIO_DIGA_"


def _parse(text: str) -> tuple[Any, Json | None]:
    try:
        return json.loads(text), None
    except json.JSONDecodeError as exc:
        where = f"line {exc.lineno}, column {exc.colno}"
        return None, {"stage": "json", "errors": [{"where": where, "message": exc.msg}]}


def _input_errors(exc: ValidationError) -> list[Json]:
    return [{"where": ".".join(str(p) for p in e["loc"]) or "(whole input)", "message": e["msg"]} for e in exc.errors()]


def _summary(bundle: Json) -> Json:
    profiles: Counter[str] = Counter()
    for entry in bundle["entry"]:
        profile = entry["resource"]["meta"]["profile"][0].rsplit("/", 1)[-1].split("|")[0]
        profiles[profile.removeprefix(_PROFILE_PREFIX)] += 1
    sections = []
    for section in bundle["entry"][0]["resource"].get("section", []):
        sections.append({"title": section["title"], "entries": len(section.get("entry", []))})
        for sub in section.get("section", []):
            sections.append({"title": f"{section['title']} › {sub['title']}", "entries": len(sub.get("entry", []))})
    return {"resources": len(bundle["entry"]), "profiles": dict(sorted(profiles.items())), "sections": sections}


def build(text: str) -> str:
    """Input JSON -> bundle, local check results and a summary; or the errors in the input."""
    raw, error = _parse(text)
    if error:
        return json.dumps(error)
    try:
        data = DigaExport.model_validate(raw)
    except ValidationError as exc:
        return json.dumps({"stage": "input", "errors": _input_errors(exc)}, ensure_ascii=False)
    bundle = build_bundle(data)
    result = {"stage": "done", "problems": check_bundle(bundle), "summary": _summary(bundle), "bundle": bundle}
    return json.dumps(result, ensure_ascii=False)


def import_medication_list(text: str) -> str:
    """ePA medication list (FHIR Bundle) -> the kit's `medications` input, plus what was skipped."""
    raw, error = _parse(text)
    if error:
        return json.dumps(error)
    try:
        result = read_medication_list(raw)
    except ValueError as exc:
        return json.dumps({"stage": "input", "errors": [{"where": "(whole input)", "message": str(exc)}]})
    medications = [m.model_dump(mode="json", exclude_none=True) for m in result.medications]
    return json.dumps(
        {
            "stage": "done",
            "medications": medications,
            "skipped": [{"where": f.reference, "message": f.reason} for f in result.skipped],
            "notes": [{"where": f.reference, "message": f.reason} for f in result.notes],
        },
        ensure_ascii=False,
    )
