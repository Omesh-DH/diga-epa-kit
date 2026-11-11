import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from diga_epa_kit import DigaExport, build_bundle, check_bundle
from diga_epa_kit.terminology.instruments import PHQ9

EXAMPLE = Path(__file__).parents[2] / "synthetic" / "archetype_a_mental" / "phq9_three_months.json"
NOW = datetime(2026, 11, 1, 9, 0, tzinfo=timezone.utc)


@pytest.fixture
def raw() -> dict:
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


@pytest.fixture
def bundle(raw) -> dict:
    return build_bundle(DigaExport.model_validate(raw), now=NOW)


def _by_type(bundle, rtype):
    return [e["resource"] for e in bundle["entry"] if e["resource"]["resourceType"] == rtype]


def test_example_passes_local_checks(bundle):
    assert check_bundle(bundle) == []


def test_scores_only_no_questionnaire_resources(bundle):
    # Decision 0007: item answers and wording never leave the DiGA.
    assert not _by_type(bundle, "Questionnaire")
    assert not _by_type(bundle, "QuestionnaireResponse")
    scores = _by_type(bundle, "Observation")
    assert [s["valueQuantity"]["value"] for s in scores] == [16, 11, 6]
    assert all("derivedFrom" not in s for s in scores)


def test_score_observation_shape(bundle):
    score = _by_type(bundle, "Observation")[0]
    (coding,) = score["code"]["coding"]
    assert (coding["code"], coding["version"]) == ("44261-6", "2.72")
    assert score["category"][0]["coding"][0]["code"] == "survey"
    (rr,) = score["referenceRange"]
    assert "text" not in rr  # max=0 in the profile
    assert (rr["low"]["value"], rr["high"]["value"]) == (PHQ9.min_score, PHQ9.max_score) == (0, 27)
    assert rr["low"]["code"] == rr["high"]["code"] == score["valueQuantity"]["code"] == "{score}"
    (device,) = _by_type(bundle, "Device")
    assert score["device"]["reference"] == f"urn:uuid:{device['id']}"


def test_scores_sit_in_the_assessment_section_only(bundle):
    sections = bundle["entry"][0]["resource"]["section"]
    assert [s["title"] for s in sections] == ["Beurteilungen"]
    refs = [e["reference"] for e in sections[0]["entry"]]
    assert refs == [f"urn:uuid:{s['id']}" for s in _by_type(bundle, "Observation")]


@pytest.mark.parametrize("score", [-1, 28])
def test_out_of_range_score_is_rejected(raw, score):
    raw["prom_scores"][0]["score"] = score
    with pytest.raises(ValidationError, match="outside 0..27"):
        DigaExport.model_validate(raw)


def test_item_answers_are_not_accepted(raw):
    raw["prom_scores"][0]["answers"] = {"q1": 2}
    with pytest.raises(ValidationError):
        DigaExport.model_validate(raw)


def test_duplicate_completion_is_rejected(raw):
    raw["prom_scores"].append(raw["prom_scores"][0])
    with pytest.raises(ValidationError, match="duplicate prom_scores"):
        DigaExport.model_validate(raw)


def test_completion_outside_period_is_rejected(raw):
    raw["prom_scores"][0]["completed_at"] = "2026-07-31T23:00:00+02:00"
    with pytest.raises(ValidationError, match="outside period"):
        DigaExport.model_validate(raw)


def test_naive_completion_time_is_rejected(raw):
    raw["prom_scores"][0]["completed_at"] = "2026-08-03T19:41:00"
    with pytest.raises(ValidationError, match="timezone"):
        DigaExport.model_validate(raw)


def test_patient_identifier_is_not_the_internal_pseudonym(raw, bundle):
    (patient,) = _by_type(bundle, "Patient")
    assert patient["identifier"][0]["value"] == f"urn:uuid:{patient['id']}"
    assert raw["patient"]["id"] not in json.dumps(bundle)


@pytest.mark.parametrize("score", [True, "16", 16.0])
def test_score_must_be_a_real_integer(raw, score):
    raw["prom_scores"][0]["score"] = score
    with pytest.raises(ValidationError):
        DigaExport.model_validate(raw)


def test_score_keeps_local_offset_and_patient_as_performer(bundle):
    score = _by_type(bundle, "Observation")[0]
    (patient,) = _by_type(bundle, "Patient")
    assert score["effectiveDateTime"] == "2026-08-03T19:41:00+02:00"
    assert score["performer"] == [{"reference": f"urn:uuid:{patient['id']}"}]
