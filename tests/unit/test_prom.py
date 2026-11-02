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


def _section(bundle, title):
    (sec,) = [s for s in bundle["entry"][0]["resource"]["section"] if s["title"] == title]
    return [e["reference"] for e in sec["entry"]]


def test_example_passes_local_checks(bundle):
    assert check_bundle(bundle) == []


def test_one_questionnaire_shared_by_all_responses(bundle):
    (q,) = _by_type(bundle, "Questionnaire")
    responses = _by_type(bundle, "QuestionnaireResponse")
    assert len(responses) == 3
    assert {r["questionnaire"] for r in responses} == {q["url"]}
    # ques-1: exactly one of title / code
    assert "title" not in q and q["code"][0]["code"] == "44249-1"


def test_scores_are_summed_and_linked(bundle):
    scores = [o for o in _by_type(bundle, "Observation") if o["code"]["coding"][0]["code"] == "44261-6"]
    assert [s["valueQuantity"]["value"] for s in scores] == [16, 11, 6]
    response_urls = {f"urn:uuid:{r['id']}" for r in _by_type(bundle, "QuestionnaireResponse")}
    assert {s["derivedFrom"][0]["reference"] for s in scores} == response_urls
    (rr,) = scores[0]["referenceRange"]
    assert "text" not in rr  # max=0 in the profile
    assert (rr["low"]["value"], rr["high"]["value"]) == (0, 27)
    assert rr["low"]["code"] == rr["high"]["code"] == scores[0]["valueQuantity"]["code"] == "{score}"


def test_answers_carry_loinc_answer_codes(bundle):
    first = _by_type(bundle, "QuestionnaireResponse")[0]
    q2 = next(i for i in first["item"] if i["linkId"] == "q2")
    assert q2["answer"][0]["valueCoding"]["code"] == "LA6571-9"  # score 3 = nearly every day


def test_sections_hold_the_right_entries(bundle):
    q_and_r = _section(bundle, "Fragebögen")
    scores = _section(bundle, "Beurteilungen")
    assert len(q_and_r) == 4 and len(scores) == 3
    titles = [s["title"] for s in bundle["entry"][0]["resource"]["section"]]
    assert titles == ["Fragebögen", "Beurteilungen"]  # profile slice order


def test_missing_answer_is_rejected(raw):
    del raw["proms"][0]["answers"]["q9"]
    with pytest.raises(ValidationError, match="missing"):
        DigaExport.model_validate(raw)


def test_out_of_range_answer_is_rejected(raw):
    raw["proms"][0]["answers"]["q1"] = 4
    with pytest.raises(ValidationError, match="out of range"):
        DigaExport.model_validate(raw)


def test_duplicate_completion_is_rejected(raw):
    raw["proms"].append(raw["proms"][0])
    with pytest.raises(ValidationError, match="duplicate proms"):
        DigaExport.model_validate(raw)


def test_completion_outside_period_is_rejected(raw):
    raw["proms"][0]["completed_at"] = "2026-07-31T23:00:00+02:00"
    with pytest.raises(ValidationError, match="outside period"):
        DigaExport.model_validate(raw)


def test_patient_identifier_is_not_the_internal_pseudonym(raw, bundle):
    (patient,) = _by_type(bundle, "Patient")
    assert patient["identifier"][0]["value"] == f"urn:uuid:{patient['id']}"
    assert raw["patient"]["id"] not in json.dumps(bundle)


def test_phq9_catalogue_shape():
    assert len(PHQ9.items) == 9 and PHQ9.max_score == 27
    assert len({i.code.code for i in PHQ9.items}) == 9
