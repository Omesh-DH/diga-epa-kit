"""Resources every export carries: Patient, the DiGA Device, its definition and manufacturer."""

from __future__ import annotations

from datetime import datetime

from ..input.model import DigaInfo, PatientInfo
from ..terminology.versions import PZN, SNOMED, VersionPack
from .common import Json, meta, ri_identifier, urn


def patient(pack: VersionPack, uuid: str, info: PatientInfo, now: datetime) -> Json:
    res: Json = {
        "resourceType": "Patient",
        "id": uuid,
        "meta": meta(pack, "patient", now),
        # The resource's own UUID, never the DiGA-internal pseudonym: that key stays in the DiGA.
        "identifier": [ri_identifier(pack, uuid)],
    }
    if info.gender:
        res["gender"] = info.gender
    if info.birth_date:
        res["birthDate"] = info.birth_date.isoformat()
    return res


def manufacturer(pack: VersionPack, uuid: str, diga: DigaInfo, now: datetime) -> Json:
    res: Json = {
        "resourceType": "Organization",
        "id": uuid,
        "meta": meta(pack, "organization_manufacturer", now),
        "identifier": [ri_identifier(pack, uuid)],
        "name": diga.manufacturer.name,
    }
    if diga.manufacturer.website:
        res["telecom"] = [{"system": "url", "value": diga.manufacturer.website}]
    return res


# German, like the section titles the profile fixes.
_SOFTWARE_VERSION = "Softwareversion"


def device_definition(pack: VersionPack, uuid: str, manufacturer_uuid: str, now: datetime) -> Json:
    return {
        "resourceType": "DeviceDefinition",
        "id": uuid,
        "meta": meta(pack, "device_definition_diga", now),
        "identifier": [ri_identifier(pack, uuid)],
        "manufacturerReference": {"reference": urn(manufacturer_uuid)},
        "type": {
            "coding": [
                {
                    "system": SNOMED,
                    "version": pack.snomed_version,
                    "code": "706689003",
                    "display": "Application program software (physical object)",
                }
            ]
        },
    }


def device(pack: VersionPack, uuid: str, definition_uuid: str, diga: DigaInfo, now: datetime) -> Json:
    """The DiGA itself; it is the Composition author and identifies via DiGA-VE-ID + PZN."""
    res: Json = {
        "resourceType": "Device",
        "id": uuid,
        "meta": meta(pack, "device_diga", now),
        "identifier": [{"type": {"text": "DiGA-VE-ID"}, "value": diga.ve_id}],
        "definition": {"reference": urn(definition_uuid)},
        "deviceName": [{"name": diga.name, "type": "user-friendly-name"}],
        "type": {"coding": [{"system": PZN, "code": diga.pzn}]},
    }
    if diga.version:
        # version.type is required by the profile; it binds no value set and the packages
        # name no code for "software version", so the kind is given as text (docs/mapping.md).
        res["version"] = [{"type": {"text": _SOFTWARE_VERSION}, "value": diga.version}]
    return res
