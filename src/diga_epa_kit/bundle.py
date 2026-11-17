"""Assemble a DigaExport into one MIO DiGA document Bundle."""

from __future__ import annotations

import uuid as _uuid
from datetime import datetime, timezone

from .input.model import DigaExport
from .mappers import composition as comp_m
from .mappers import core, goals, medication, prom, reports, results, vitals
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
    height_ids = [_id("body-height", data.patient.id, h.measured_at.isoformat()) for h in data.body_heights]
    bp_ids = [_id("blood-pressure", data.patient.id, b.measured_at.isoformat()) for b in data.blood_pressures]
    bmi_ids = [_id("bmi", data.patient.id, b.measured_at.isoformat()) for b in data.body_mass_indices]
    step_ids = [_id("daily-steps", data.patient.id, s.day.isoformat()) for s in data.daily_steps]

    body = [
        core.patient(pack, patient_id, data.patient, now),
        core.device(pack, device_id, devdef_id, data.diga, now),
        core.device_definition(pack, devdef_id, org_id, now),
        core.manufacturer(pack, org_id, data.diga, now),
        *(
            vitals.body_weight(pack, wid, patient_id, w, now)
            for wid, w in zip(weight_ids, data.body_weights, strict=True)
        ),
        *(
            vitals.body_height(pack, hid, patient_id, h, now)
            for hid, h in zip(height_ids, data.body_heights, strict=True)
        ),
        *(
            vitals.blood_pressure(pack, bid, patient_id, b, now)
            for bid, b in zip(bp_ids, data.blood_pressures, strict=True)
        ),
        *(
            results.body_mass_index(pack, bid, patient_id, device_id, b, now)
            for bid, b in zip(bmi_ids, data.body_mass_indices, strict=True)
        ),
        *(
            results.daily_steps(pack, sid, patient_id, s, now)
            for sid, s in zip(step_ids, data.daily_steps, strict=True)
        ),
    ]

    # (profile key, [(time, value)]) in the kit's own fixed order; the profile does not order entries.
    simple_vitals: list[tuple[str, list[tuple[datetime, float]]]] = [
        ("heart_rate", [(r.measured_at, r.bpm) for r in data.heart_rates]),
        ("body_temperature", [(r.measured_at, round(r.celsius, 1)) for r in data.body_temperatures]),
        ("oxygen_saturation", [(r.measured_at, r.percent) for r in data.oxygen_saturations]),
        ("respiratory_rate", [(r.measured_at, r.per_minute) for r in data.respiratory_rates]),
    ]
    simple_ids: list[str] = []
    for kind, readings in simple_vitals:
        for measured_at, value in readings:
            vital_id = _id(kind.replace("_", "-"), data.patient.id, measured_at.isoformat())
            body.append(vitals.simple_vital(pack, kind, vital_id, patient_id, measured_at, value, now))
            simple_ids.append(vital_id)

    for reading in data.glucose_readings:
        glucose_id = _id("glucose", data.patient.id, reading.specimen, reading.measured_at.isoformat())
        body.append(vitals.glucose(pack, glucose_id, patient_id, reading, now))
        simple_ids.append(glucose_id)

    score_ids: list[str] = []
    for p in data.prom_scores:
        inst = INSTRUMENTS[p.instrument]
        score_id = _id("score", data.patient.id, inst.key, p.completed_at.isoformat())
        body.append(prom.score(pack, score_id, patient_id, device_id, inst, p, now))
        score_ids.append(score_id)

    goal_ids = {g.id: _id("goal", data.patient.id, g.id) for g in data.goals}
    body.extend(goals.goal(pack, goal_ids[g.id], patient_id, g, now) for g in data.goals)
    plan_ids: list[str] = []
    for plan in data.care_plans:
        plan_id = _id("care-plan", data.patient.id, plan.id)
        body.append(goals.care_plan(pack, plan_id, patient_id, [goal_ids[g] for g in plan.goal_ids], plan, now))
        plan_ids.append(plan_id)

    statement_ids: list[str] = []
    for med in data.medications:
        drug_id = _id("medication", data.patient.id, med.id)
        statement_id = _id("medication-statement", data.patient.id, med.id)
        body.append(medication.medication(pack, drug_id, med, now))
        body.append(medication.medication_statement(pack, statement_id, patient_id, drug_id, med, now))
        statement_ids.append(statement_id)

    diary_ids: list[str] = []
    for d in data.diary_entries:
        diary_id = _id("diary-entry", data.patient.id, d.written_at.isoformat())
        body.append(reports.diary_entry(pack, diary_id, patient_id, d, now))
        diary_ids.append(diary_id)

    comp = comp_m.composition(
        pack,
        _id("composition", *key),
        patient_id,
        device_id,
        (data.period_start, data.period_end),
        now,
        results=[*bmi_ids, *step_ids],
        vital_signs=[*weight_ids, *height_ids, *bp_ids, *simple_ids],
        medications=statement_ids,
        assessments=score_ids,
        goals=[*goal_ids.values(), *plan_ids],
        patient_reports=diary_ids,
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
