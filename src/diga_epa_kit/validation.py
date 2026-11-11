"""Fast local checks that mirror the MIO DiGA Bundle invariants.

These are not a substitute for the FHIR validator. They catch the structural
mistakes that are cheap to detect in-process, so unit tests and the CLI give
feedback without a JVM.
"""

from __future__ import annotations

from typing import Any

from .terminology.versions import KBV_SD


def check_bundle(bundle: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    if bundle.get("resourceType") != "Bundle" or bundle.get("type") != "document":
        return ["not a document Bundle"]

    entries = bundle.get("entry") or []
    if not entries:
        return ["Bundle has no entries"]

    full_urls = {e.get("fullUrl") for e in entries}
    if len(full_urls) != len(entries):
        problems.append("duplicate entry.fullUrl")

    # A canonical is not a Reference, so the reference walk below never sees it.
    questionnaires = {
        f"{q.get('url')}|{q.get('version')}"
        for q in (e.get("resource") or {} for e in entries)
        if q.get("resourceType") == "Questionnaire"
    }

    bundle_version = _profile_version(bundle)
    compositions = 0
    for i, e in enumerate(entries):
        res = e.get("resource") or {}
        where = f"entry[{i}] {res.get('resourceType')}"
        profiles = (res.get("meta") or {}).get("profile") or []
        mio = [p for p in profiles if p.startswith(KBV_SD + "KBV_PR_MIO_DIGA")]
        if not mio:
            # bundle-1: every entry must claim a MIO DiGA profile
            problems.append(f"{where}: no MIO DiGA meta.profile")
            continue
        if any(p.rpartition("|")[2] != bundle_version for p in mio):
            problems.append(f"{where}: profile version differs from Bundle ({bundle_version})")
        if any(p.startswith(KBV_SD + "KBV_PR_MIO_DIGA_Composition|") for p in mio):
            compositions += 1
        for ref in _references(res):
            if ref.startswith("urn:uuid:") and ref not in full_urls:
                problems.append(f"{where}: unresolved reference {ref}")
        if res.get("resourceType") == "QuestionnaireResponse" and res.get("questionnaire") not in questionnaires:
            problems.append(f"{where}: questionnaire {res.get('questionnaire')} matches no Questionnaire in the Bundle")

    # bundle-2: exactly one Composition, and FHIR wants it first
    if compositions != 1:
        problems.append(f"expected exactly one Composition, found {compositions}")
    elif (entries[0].get("resource") or {}).get("resourceType") != "Composition":
        problems.append("Composition is not the first entry")
    return problems


def _profile_version(res: dict[str, Any]) -> str:
    profiles = (res.get("meta") or {}).get("profile") or [""]
    return profiles[0].rpartition("|")[2]


def _references(node: Any):
    if isinstance(node, dict):
        for k, v in node.items():
            if k == "reference" and isinstance(v, str):
                yield v
            else:
                yield from _references(v)
    elif isinstance(node, list):
        for v in node:
            yield from _references(v)
