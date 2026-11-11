"""Goals and care plans (section Ziele)."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from ..input.model import CarePlan, Goal
from ..terminology.versions import VersionPack
from .common import Json, meta, ri_identifier, urn

# Input wording to the codes of the base FHIR value sets goal-status,
# request-status and care-plan-activity-status (all required bindings in FHIR R4).
_GOAL_STATUS = {"active": "active", "on_hold": "on-hold", "completed": "completed", "cancelled": "cancelled"}
_PLAN_STATUS = {"active": "active", "on_hold": "on-hold", "completed": "completed", "revoked": "revoked"}
_ACTIVITY_STATUS = {
    "not_started": "not-started",
    "scheduled": "scheduled",
    "in_progress": "in-progress",
    "on_hold": "on-hold",
    "completed": "completed",
    "cancelled": "cancelled",
}
_GOAL_END = "https://fhir.kbv.de/StructureDefinition/KBV_EX_Base_Treatment_Goal_End"


def goal(pack: VersionPack, uuid: str, patient_uuid: str, g: Goal, now: datetime) -> Json:
    res: Json = {
        "resourceType": "Goal",
        "id": uuid,
        "meta": meta(pack, "goal", now),
    }
    if g.end is not None:
        res["extension"] = [{"url": _GOAL_END, "valueDate": g.end.isoformat()}]
    res |= {
        "identifier": [ri_identifier(pack, uuid)],
        "lifecycleStatus": _GOAL_STATUS[g.status],
        # Free text only: the kit has no coded goal catalogue, and a target would need a coded measure.
        "description": {"text": g.description},
        "subject": {"reference": urn(patient_uuid)},
        "startDate": g.start.isoformat(),
    }
    if g.set_by_patient:
        # Only a person may be named here, never the DiGA (docs/gaps.md G8).
        res["expressedBy"] = {"reference": urn(patient_uuid)}
    return res


def care_plan(
    pack: VersionPack, uuid: str, patient_uuid: str, goal_uuids: Sequence[str], plan: CarePlan, now: datetime
) -> Json:
    activities = []
    for a in plan.activities:
        detail: Json = {"status": _ACTIVITY_STATUS[a.status]}
        if a.start is not None or a.end is not None:
            period = {"start": a.start.isoformat() if a.start else None, "end": a.end.isoformat() if a.end else None}
            detail["scheduledPeriod"] = {k: v for k, v in period.items() if v}
        # The patient carries out the activities of a DiGA plan.
        detail["performer"] = [{"reference": urn(patient_uuid)}]
        detail["description"] = a.description
        activities.append({"detail": detail})

    res: Json = {
        "resourceType": "CarePlan",
        "id": uuid,
        "meta": meta(pack, "care_plan", now),
        "identifier": [ri_identifier(pack, uuid)],
        "status": _PLAN_STATUS[plan.status],
        "intent": "plan",  # pattern of the profile
        "title": plan.title,
        "subject": {"reference": urn(patient_uuid)},
    }
    if plan.written_by_patient:
        # Only a person may be named here, never the DiGA (docs/gaps.md G8).
        res["author"] = {"reference": urn(patient_uuid)}
    if goal_uuids:
        res["goal"] = [{"reference": urn(u)} for u in goal_uuids]
    res["activity"] = activities
    return res
