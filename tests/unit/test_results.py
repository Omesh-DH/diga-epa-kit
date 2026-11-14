import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from diga_epa_kit import DigaExport, build_bundle, check_bundle

EXAMPLE = Path(__file__).parents[2] / "synthetic" / "archetype_b_metabolic" / "weight_bmi_and_steps.json"
NOW = datetime(2026, 11, 1, 9, 0, tzinfo=timezone.utc)
PROFILE = "https://fhir.kbv.de/StructureDefinition/KBV_PR_MIO_DIGA_Observation_Free|1.1.0"


@pytest.fixture
def raw() -> dict:
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


@pytest.fixture
def bundle(raw) -> dict:
    return build_bundle(DigaExport.model_validate(raw), now=NOW)


def _free(bundle, code):
    return [
        e["resource"]
        for e in bundle["entry"]
        if e["resource"]["meta"]["profile"] == [PROFILE] and e["resource"]["code"]["coding"][0]["code"] == code
    ]


def _one(bundle, rtype):
    (res,) = [e["resource"] for e in bundle["entry"] if e["resource"]["resourceType"] == rtype]
    return res


def test_example_passes_local_checks(bundle):
    assert check_bundle(bundle) == []


def test_bmi_shape(bundle):
    first, last = _free(bundle, "39156-5")
    assert first["code"] == {
        "coding": [
            {
                "system": "http://loinc.org",
                "version": "2.72",
                "code": "39156-5",
                "display": "Body mass index (BMI) [Ratio]",
            }
        ]
    }
    assert first["status"] == "final"
    assert first["category"] == [
        {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "vital-signs"}]}
    ]
    assert first["valueQuantity"] == {
        "value": 32.8,
        "unit": "kg/m2",
        "system": "http://unitsofmeasure.org",
        "code": "kg/m2",
    }
    assert last["valueQuantity"]["value"] == 32.5
    # The offset changes with the clock change on 25 October.
    assert first["effectiveDateTime"] == "2026-10-19T07:10:00+02:00"
    assert last["effectiveDateTime"] == "2026-10-25T08:05:00+01:00"
    assert first["subject"] == {"reference": f"urn:uuid:{_one(bundle, 'Patient')['id']}"}
    # Calculated by the app: the DiGA is the device and nobody is the performer.
    assert first["device"] == {"reference": f"urn:uuid:{_one(bundle, 'Device')['id']}"}
    assert "performer" not in first


def test_daily_steps_shape(bundle):
    steps = _free(bundle, "41950-7")
    assert [s["valueQuantity"]["value"] for s in steps] == [4210, 5630, 2890, 7340, 6125, 9480, 8015]
    first = steps[0]
    assert first["code"] == {
        "coding": [
            {
                "system": "http://loinc.org",
                "version": "2.72",
                "code": "41950-7",
                "display": "Number of steps in 24 hour Measured",
            }
        ]
    }
    assert first["category"] == [
        {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "activity"}]}
    ]
    assert first["valueQuantity"] == {
        "value": 4210,
        "unit": "Schritte/24 h",
        "system": "http://unitsofmeasure.org",
        "code": "{#}/(24.h)",
    }
    # A calendar day, without time or offset.
    assert [s["effectiveDateTime"] for s in steps][:2] == ["2026-10-19", "2026-10-20"]
    assert first["performer"] == [{"reference": f"urn:uuid:{_one(bundle, 'Patient')['id']}"}]
    assert "device" not in first


def test_profile_prohibitions_are_respected(bundle):
    for obs in _free(bundle, "39156-5") + _free(bundle, "41950-7"):
        assert not {"implicitRules", "language", "contained", "specimen"} & set(obs)
        assert not {"source", "security", "tag"} & set(obs["meta"])
        assert obs["meta"]["versionId"] and obs["meta"]["lastUpdated"]


def test_free_results_are_entries_of_the_results_section(bundle):
    results, goals = bundle["entry"][0]["resource"]["section"]
    assert (results["title"], goals["title"]) == ("Befunde und Ergebnisse", "Ziele")
    free_ids = [f"urn:uuid:{o['id']}" for o in _free(bundle, "39156-5") + _free(bundle, "41950-7")]
    assert [e["reference"] for e in results["entry"]] == free_ids
    (vitals,) = results["section"]
    assert vitals["title"] == "Vitalzeichen und Körpermaße"
    assert len(vitals["entry"]) == 2 and not set(free_ids) & {e["reference"] for e in vitals["entry"]}


def test_results_section_without_vital_signs_has_no_subsection(raw):
    del raw["body_weights"]
    results = build_bundle(DigaExport.model_validate(raw), now=NOW)["entry"][0]["resource"]["section"][0]
    assert "section" not in results and len(results["entry"]) == 9


def test_ids_are_stable_and_unique(raw, bundle):
    again = build_bundle(DigaExport.model_validate(raw), now=NOW)
    ids = [e["resource"]["id"] for e in bundle["entry"]]
    assert ids == [e["resource"]["id"] for e in again["entry"]]
    assert len(set(ids)) == len(ids)


def test_bmi_is_rounded_to_one_decimal(raw):
    raw["body_mass_indices"][0]["kg_m2"] = 32.84
    bundle = build_bundle(DigaExport.model_validate(raw), now=NOW)
    assert _free(bundle, "39156-5")[0]["valueQuantity"]["value"] == 32.8


@pytest.mark.parametrize("value", [4.9, 150.1, -1])
def test_implausible_bmi_is_rejected(raw, value):
    raw["body_mass_indices"][0]["kg_m2"] = value
    with pytest.raises(ValidationError):
        DigaExport.model_validate(raw)


def test_naive_bmi_time_is_rejected(raw):
    raw["body_mass_indices"][0]["measured_at"] = "2026-10-19T07:10:00"
    with pytest.raises(ValidationError, match="timezone"):
        DigaExport.model_validate(raw)


def test_duplicate_bmi_is_rejected(raw):
    raw["body_mass_indices"].append(raw["body_mass_indices"][0])
    with pytest.raises(ValidationError, match="duplicate body_mass_indices"):
        DigaExport.model_validate(raw)


def test_bmi_outside_period_is_rejected(raw):
    raw["body_mass_indices"][0]["measured_at"] = "2026-10-18T23:00:00+02:00"
    with pytest.raises(ValidationError, match="outside period"):
        DigaExport.model_validate(raw)


@pytest.mark.parametrize("steps", [0, 200_000])
def test_step_bounds_are_accepted(raw, steps):
    raw["daily_steps"][0]["steps"] = steps
    assert DigaExport.model_validate(raw).daily_steps[0].steps == steps


@pytest.mark.parametrize("steps", [-1, 200_001, 4210.0, "4210", True])
def test_bad_step_count_is_rejected(raw, steps):
    raw["daily_steps"][0]["steps"] = steps
    with pytest.raises(ValidationError):
        DigaExport.model_validate(raw)


def test_duplicate_day_is_rejected(raw):
    raw["daily_steps"].append(raw["daily_steps"][0])
    with pytest.raises(ValidationError, match="duplicate daily_steps"):
        DigaExport.model_validate(raw)


def test_day_outside_period_is_rejected(raw):
    raw["daily_steps"][0]["day"] = "2026-10-26"
    with pytest.raises(ValidationError, match="outside period"):
        DigaExport.model_validate(raw)


def test_unknown_field_is_rejected(raw):
    raw["daily_steps"][0]["source"] = "phone"
    with pytest.raises(ValidationError):
        DigaExport.model_validate(raw)


def test_bmi_without_steps_and_steps_without_bmi(raw):
    for dropped, kept, n in (("daily_steps", "39156-5", 2), ("body_mass_indices", "41950-7", 7)):
        data = {k: v for k, v in raw.items() if k != dropped}
        bundle = build_bundle(DigaExport.model_validate(data), now=NOW)
        results = bundle["entry"][0]["resource"]["section"][0]
        assert [e["reference"] for e in results["entry"]] == [f"urn:uuid:{o['id']}" for o in _free(bundle, kept)]
        assert len(results["entry"]) == n


def test_vitals_only_results_section_has_no_direct_entries(raw):
    del raw["body_mass_indices"], raw["daily_steps"]
    results = build_bundle(DigaExport.model_validate(raw), now=NOW)["entry"][0]["resource"]["section"][0]
    assert "entry" not in results and len(results["section"][0]["entry"]) == 2


def test_entries_keep_input_order(raw):
    raw["daily_steps"].reverse()
    bundle = build_bundle(DigaExport.model_validate(raw), now=NOW)
    assert [s["effectiveDateTime"] for s in _free(bundle, "41950-7")][0] == "2026-10-25"


def test_goals_without_a_care_plan(bundle):
    # Archetype B sets goals but has no therapy plan: the section lists the goals only.
    goals = [e["resource"] for e in bundle["entry"] if e["resource"]["resourceType"] == "Goal"]
    assert [g["lifecycleStatus"] for g in goals] == ["active", "active"]
    assert not [e for e in bundle["entry"] if e["resource"]["resourceType"] == "CarePlan"]
    section = bundle["entry"][0]["resource"]["section"][1]
    assert [e["reference"] for e in section["entry"]] == [f"urn:uuid:{g['id']}" for g in goals]
    patient = _one(bundle, "Patient")
    weight, steps = goals
    # Only the goal the patient set names the patient as its source (docs/gaps.md G8).
    assert weight["expressedBy"] == {"reference": f"urn:uuid:{patient['id']}"}
    assert "expressedBy" not in steps
    assert (weight["startDate"], steps["startDate"]) == ("2026-09-01", "2026-10-05")
    # No end date, no end extension.
    assert "extension" not in steps
