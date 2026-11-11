import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from diga_epa_kit import DigaExport, build_bundle, check_bundle

EXAMPLE = Path(__file__).parents[2] / "synthetic" / "archetype_d_exercise" / "back_exercise_plan.json"
NOW = datetime(2026, 10, 1, 9, 0, tzinfo=timezone.utc)


@pytest.fixture
def raw() -> dict:
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


@pytest.fixture
def bundle(raw) -> dict:
    return build_bundle(DigaExport.model_validate(raw), now=NOW)


def _by_type(bundle, rtype):
    return [e["resource"] for e in bundle["entry"] if e["resource"]["resourceType"] == rtype]


def _patient_ref(bundle):
    (patient,) = _by_type(bundle, "Patient")
    return {"reference": f"urn:uuid:{patient['id']}"}


def test_example_passes_local_checks(bundle):
    assert check_bundle(bundle) == []


def test_goal_shape(bundle):
    walk, routine = _by_type(bundle, "Goal")
    assert walk["meta"]["profile"] == ["https://fhir.kbv.de/StructureDefinition/KBV_PR_MIO_DIGA_Goal|1.1.0"]
    assert walk["lifecycleStatus"] == "active" and routine["lifecycleStatus"] == "completed"
    assert walk["description"] == {"text": "Wieder 30 Minuten am Stück spazieren gehen"}
    assert walk["subject"] == _patient_ref(bundle)
    assert walk["startDate"] == "2026-08-24"
    assert walk["extension"] == [
        {"url": "https://fhir.kbv.de/StructureDefinition/KBV_EX_Base_Treatment_Goal_End", "valueDate": "2026-11-15"}
    ]
    # Prohibited by the profile, or needing content the input does not carry.
    assert not {"category", "statusDate", "statusReason", "addresses", "target"} & walk.keys()
    # Named only when the input says the patient set the goal.
    assert walk["expressedBy"] == _patient_ref(bundle)
    assert "expressedBy" not in routine


def test_plan_author_only_when_the_patient_wrote_it(raw, bundle):
    assert "author" not in _by_type(bundle, "CarePlan")[0]
    raw["care_plans"][0]["written_by_patient"] = True
    (plan,) = _by_type(build_bundle(DigaExport.model_validate(raw), now=NOW), "CarePlan")
    assert plan["author"] == {"reference": f"urn:uuid:{_by_type(bundle, 'Patient')[0]['id']}"}


def test_status_words_map_to_fhir_codes(raw):
    raw["goals"][0]["status"] = "on_hold"
    raw["goals"][1]["status"] = "cancelled"
    raw["care_plans"][0]["status"] = "on_hold"
    acts = raw["care_plans"][0]["activities"]
    acts[0]["status"], acts[1]["status"], acts[2]["status"] = "cancelled", "on_hold", "scheduled"
    bundle = build_bundle(DigaExport.model_validate(raw), now=NOW)
    assert [g["lifecycleStatus"] for g in _by_type(bundle, "Goal")] == ["on-hold", "cancelled"]
    (plan,) = _by_type(bundle, "CarePlan")
    assert plan["status"] == "on-hold"
    assert [a["detail"]["status"] for a in plan["activity"]] == ["cancelled", "on-hold", "scheduled"]


def test_revoked_plan_and_subset_of_goals(raw):
    plan_in = raw["care_plans"][0]
    plan_in.update({"status": "revoked", "goal_ids": ["goal-routine"]})
    for a in plan_in["activities"]:
        a["status"] = "cancelled"
    bundle = build_bundle(DigaExport.model_validate(raw), now=NOW)
    (plan,) = _by_type(bundle, "CarePlan")
    assert plan["status"] == "revoked"
    assert plan["goal"] == [{"reference": f"urn:uuid:{_by_type(bundle, 'Goal')[1]['id']}"}]


def test_activity_with_only_an_end_date(raw):
    del raw["care_plans"][0]["activities"][0]["start"]
    (plan,) = _by_type(build_bundle(DigaExport.model_validate(raw), now=NOW), "CarePlan")
    assert plan["activity"][0]["detail"]["scheduledPeriod"] == {"end": "2026-09-13"}


def test_goal_without_end_has_no_extension(raw):
    del raw["goals"][0]["end"]
    goal = _by_type(build_bundle(DigaExport.model_validate(raw), now=NOW), "Goal")[0]
    assert "extension" not in goal


def test_care_plan_shape(bundle):
    (plan,) = _by_type(bundle, "CarePlan")
    assert plan["meta"]["profile"] == ["https://fhir.kbv.de/StructureDefinition/KBV_PR_MIO_DIGA_CarePlan|1.1.0"]
    assert (plan["status"], plan["intent"], plan["title"]) == ("active", "plan", "Übungsprogramm Rücken, Stufe 1")
    assert plan["subject"] == _patient_ref(bundle)
    assert plan["goal"] == [{"reference": f"urn:uuid:{g['id']}"} for g in _by_type(bundle, "Goal")]
    prohibited = {"category", "description", "period", "created", "contributor", "careTeam", "addresses", "encounter"}
    assert not prohibited & plan.keys()


def test_care_plan_activities(bundle):
    (plan,) = _by_type(bundle, "CarePlan")
    done, current, later = (a["detail"] for a in plan["activity"])
    assert [d["status"] for d in (done, current, later)] == ["completed", "in-progress", "not-started"]
    assert done["scheduledPeriod"] == {"start": "2026-08-24", "end": "2026-09-13"}
    assert "scheduledPeriod" not in later
    assert done["description"] == "Mobilisation der Lendenwirbelsäule, 10 Minuten"
    assert all(d["performer"] == [_patient_ref(bundle)] for d in (done, current, later))
    prohibited = {"kind", "reasonReference", "statusReason", "location", "dailyAmount"}
    assert all(not prohibited & d.keys() for d in (done, current, later))
    assert all(a.keys() == {"detail"} for a in plan["activity"])


def test_activity_with_only_a_start_date(raw):
    del raw["care_plans"][0]["activities"][1]["end"]
    (plan,) = _by_type(build_bundle(DigaExport.model_validate(raw), now=NOW), "CarePlan")
    assert plan["activity"][1]["detail"]["scheduledPeriod"] == {"start": "2026-09-14"}


def test_goals_section_sits_between_assessments_and_reports(raw, bundle):
    goals_section, reports = bundle["entry"][0]["resource"]["section"]
    assert goals_section["title"] == "Ziele" and reports["title"] == "Patientenberichte"
    assert goals_section["code"] == {
        "coding": [
            {
                "system": "https://fhir.kbv.de/CodeSystem/KBV_CS_MIO_DIGA_Section_Codes",
                "version": "1.1.0",
                "code": "SectionZiele",
                "display": "Bereich Ziele",
            }
        ]
    }
    expected = [*_by_type(bundle, "Goal"), *_by_type(bundle, "CarePlan")]
    assert [e["reference"] for e in goals_section["entry"]] == [f"urn:uuid:{r['id']}" for r in expected]

    raw["prom_scores"] = [{"instrument": "phq9", "completed_at": "2026-09-05T10:00:00+02:00", "score": 3}]
    full = build_bundle(DigaExport.model_validate(raw), now=NOW)
    titles = [s["title"] for s in full["entry"][0]["resource"]["section"]]
    assert titles == ["Beurteilungen", "Ziele", "Patientenberichte"]


def test_internal_keys_are_not_exported(bundle):
    dumped = json.dumps(bundle)
    assert "goal-walk" not in dumped and "plan-back-1" not in dumped


def test_plan_without_goals_has_no_goal_element(raw):
    raw["care_plans"][0]["goal_ids"] = []
    (plan,) = _by_type(build_bundle(DigaExport.model_validate(raw), now=NOW), "CarePlan")
    assert "goal" not in plan


@pytest.mark.parametrize(
    "path, patch, match",
    [
        (("goals", 0), {"end": "2026-08-01"}, "end is before start"),
        (("goals", 0), {"description": "  "}, "blank or padded"),
        (("goals", 0), {"description": "a\x00b"}, "control characters"),
        (("goals", 0), {"status": "proposed"}, "status"),
        (("goals", 0), {"id": "has space"}, "pattern"),
        (("goals", 1), {"id": "goal-walk"}, "duplicate goals.id"),
        (("care_plans", 0), {"goal_ids": ["goal-none"]}, "unknown goals"),
        (("care_plans", 0), {"goal_ids": ["goal-walk", "goal-walk"]}, "duplicate goal_ids"),
        (("care_plans", 0), {"activities": []}, "at least 1"),
        (("care_plans", 0), {"title": ""}, "at least 1"),
        (("care_plans", 0), {"status": "draft"}, "status"),
        (("care_plans", 0), {"status": "completed"}, "open activities"),
        (("care_plans", 0), {"status": "revoked"}, "open activities"),
        (("goals", 0), {"start": "2026-10-01", "end": "2026-11-15"}, "starts after period_end"),
    ],
)
def test_bad_input_is_rejected(raw, path, patch, match):
    raw[path[0]][path[1]].update(patch)
    with pytest.raises(ValidationError, match=match):
        DigaExport.model_validate(raw)


def test_activity_end_before_start_is_rejected(raw):
    raw["care_plans"][0]["activities"][0].update({"start": "2026-09-10", "end": "2026-09-01"})
    with pytest.raises(ValidationError, match="end is before start"):
        DigaExport.model_validate(raw)


@pytest.mark.parametrize(
    "patch, match",
    [
        ({"status": "done"}, "status"),
        ({"description": "padded "}, "blank or padded"),
        ({"start": "2026-10-01", "end": "2026-10-11"}, "starts after period_end"),
    ],
)
def test_bad_activity_is_rejected(raw, patch, match):
    raw["care_plans"][0]["activities"][1].update(patch)
    with pytest.raises(ValidationError, match=match):
        DigaExport.model_validate(raw)


@pytest.mark.parametrize("path", [("goals", 0), ("care_plans", 0)])
def test_status_is_required(raw, path):
    del raw[path[0]][path[1]]["status"]
    with pytest.raises(ValidationError, match="status"):
        DigaExport.model_validate(raw)


def test_activity_status_is_required(raw):
    del raw["care_plans"][0]["activities"][0]["status"]
    with pytest.raises(ValidationError, match="status"):
        DigaExport.model_validate(raw)


def test_duplicate_plan_id_is_rejected(raw):
    raw["care_plans"].append(raw["care_plans"][0])
    with pytest.raises(ValidationError, match="duplicate care_plans.id"):
        DigaExport.model_validate(raw)
