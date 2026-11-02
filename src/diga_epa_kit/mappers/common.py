"""Helpers every mapper uses. Resources are plain FHIR JSON dicts.

Every mapper takes the version pack explicitly so a bundle never mixes
profile versions (KBV_PR_MIO_DIGA_Bundle invariant bundle-1 rejects that).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from ..terminology.instruments import Code
from ..terminology.versions import LOINC, RFC3986, V2_0203, VersionPack

Json = dict[str, Any]


def urn(uuid: str) -> str:
    return f"urn:uuid:{uuid}"


def meta(pack: VersionPack, profile_key: str, last_updated: datetime) -> Json:
    return {
        "versionId": "1",
        "lastUpdated": last_updated.isoformat(),
        "profile": [pack.profile(profile_key)],
    }


def ri_identifier(pack: VersionPack, uuid: str) -> Json:
    """Resource identifier (v2-0203 RI) that most MIO DiGA profiles require."""
    return {
        "type": {
            "coding": [
                {
                    "system": V2_0203,
                    "version": pack.v2_0203_version,
                    "code": "RI",
                    "display": "Resource identifier",
                }
            ]
        },
        "system": RFC3986,
        "value": urn(uuid),
    }


def loinc(pack: VersionPack, c: Code) -> Json:
    return {"system": LOINC, "version": pack.loinc_version, "code": c.code, "display": c.display}
