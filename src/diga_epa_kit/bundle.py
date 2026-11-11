"""Assemble a DigaExport into one MIO DiGA document Bundle."""

from __future__ import annotations

import uuid as _uuid
from datetime import datetime, timezone

from .input.model import DigaExport
from .mappers import composition as comp_m
from .mappers import core, prom, vitals
from .mappers.common import Json, ri_identifier, urn
from .terminology.instruments import INSTRUMENTS
from .terminology.versions import DEFAULT_VERSION, get_pack

# Fixed namespace so the same input always yields the same resource ids, which
# keeps exports diffable and lets the ePA side de-duplicate re-sent bundles.
_NS = _uuid.UUID("6f1c2a8e-3d4b-5c6d-8e9f-0a1b2c3d4e5f")


def _id(*parts: object) -> str:
    return str(_uuid.uuid5(_NS, "|".join(str(p) for p in parts)))


def build_bundle(data: DigaExport, version: str = DEFAULT_VERSION, now: datetime | None = None) -> Json:
    pack = get_pack(version)
    now = (now or datetime.now(timezone.utc)).replace(microsecond=0)
    key = (data.diga.ve_id, data.patient.id, data.period_start, data.period_end)

    patient_id = _id("patient", data.patient.id)
    org_id = _id("manufacturer", data.diga.manufacturer.name)
    devdef_id = _id("device-definition", data.diga.ve_id)
    device_id = _id("device", data.diga.ve_id)
    weight_ids = [_id("body-weight", data.patient.id, w.measured_at.isoformat()) for w in data.body_weights]

    body = [
        core.patient(pack, patient_id, data.patient, now),
        core.device(pack, device_id, devdef_id, data.diga, now),
        core.device_definition(pack, devdef_id, org_id, now),
        core.manufacturer(pack, org_id, data.diga, now),
        *(vitals.body_weight(pack, wid, patient_id, w, now) for wid, w in zip(weight_ids, data.body_weights)),
    ]

    score_ids: list[str] = []
    for p in data.prom_scores:
        inst = INSTRUMENTS[p.instrument]
        score_id = _id("score", data.patient.id, inst.key, p.completed_at.isoformat())
        body.append(prom.score(pack, score_id, patient_id, device_id, inst, p, now))
        score_ids.append(score_id)

    comp = comp_m.composition(
        pack,
        _id("composition", *key),
        patient_id,
        device_id,
        (data.period_start, data.period_end),
        now,
        vital_signs=weight_ids,
        assessments=score_ids,
    )
    bundle_id = _id("bundle", *key, now.isoformat())

    return {
        "resourceType": "Bundle",
        "id": bundle_id,
        "meta": {"versionId": "1", "lastUpdated": now.isoformat(), "profile": [pack.profile("bundle")]},
        "identifier": ri_identifier(pack, bundle_id),
        "type": "document",
        "timestamp": now.isoformat(),
        # A document Bundle must start with its Composition.
        "entry": [{"fullUrl": urn(res["id"]), "resource": res} for res in (comp, *body)],
    }
