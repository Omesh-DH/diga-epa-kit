import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from diga_epa_kit import DigaExport, build_bundle, check_bundle
from diga_epa_kit.terminology.instruments import GAD7

EXAMPLE = Path(__file__).parents[2] / "synthetic" / "archetype_a_mental" / "phq9_and_mood_diary.json"
NOW = datetime(2026, 11, 1, 9, 0, tzinfo=timezone.utc)
SCORE_PROFILE = "https://fhir.kbv.de/StructureDefinition/KBV_PR_MIO_DIGA_Observation_Score_or_Assessment_by_Scale|1.1.0"


@pytest.fixture
def raw() -> dict:
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


@pytest.fixture
def bundle(raw) -> dict:
    return build_bundle(DigaExport.model_validate(raw), now=NOW)


def _gad7(bundle):
    return [
        e["resource"]
        for e in bundle["entry"]
        if e["resource"]["resourceType"] == "Observation"
        and e["resource"]["code"]["coding"][0]["code"] == "70274-6"
    ]


def test_example_passes_local_checks(bundle):
    assert check_bundle(bundle) == []


def test_anxiety_score_shape(bundle):
    first, last = _gad7(bundle)
    assert first["meta"]["profile"] == [SCORE_PROFILE]
    assert first["code"] == {
        "coding": [
            {
                "system": "http://loinc.org",
                "version": "2.72",
                "code": "70274-6",
                "display": "Generalized anxiety disorder 7 item (GAD-7) total score [Reported.PHQ]",
            }
        ]
    }
    assert (first["valueQuantity"]["value"], last["valueQuantity"]["value"]) == (11, 7)
    assert first["valueQuantity"]["code"] == "{score}"
    assert first["category"][0]["coding"][0]["code"] == "survey"
    assert first["effectiveDateTime"] == "2026-08-02T20:20:00+02:00"
    assert last["effectiveDateTime"] == "2026-08-30T19:55:00+02:00"
    assert last["code"] == first["code"] and last["referenceRange"] == first["referenceRange"]
    (rr,) = first["referenceRange"]
    assert (rr["low"]["value"], rr["high"]["value"]) == (GAD7.min_score, GAD7.max_score) == (0, 21)
    assert rr["type"] == {"text": "Wertebereich der Skala"}
    assert "text" not in rr
    patient = next(e["resource"] for e in bundle["entry"] if e["resource"]["resourceType"] == "Patient")
    device = next(e["resource"] for e in bundle["entry"] if e["resource"]["resourceType"] == "Device")
    assert first["performer"] == [{"reference": f"urn:uuid:{patient['id']}"}]
    assert first["device"] == {"reference": f"urn:uuid:{device['id']}"}


def test_both_instruments_share_the_assessment_section(bundle):
    (assessments,) = [
        s
        for s in bundle["entry"][0]["resource"]["section"]
        if s["code"]["coding"][0]["code"] == "424836000"  # pattern of the beurteilungen slice
    ]
    assert assessments["title"] == "Beurteilungen"
    refs = [e["reference"] for e in assessments["entry"]]
    assert len(refs) == len(set(refs)) == 4
    by_url = {e["fullUrl"]: e["resource"] for e in bundle["entry"]}
    assert all(by_url[r]["meta"]["profile"] == [SCORE_PROFILE] for r in refs)
    assert {f"urn:uuid:{s['id']}" for s in _gad7(bundle)} <= set(refs)


@pytest.mark.parametrize("score", [0, 21])
def test_scale_ends_are_accepted(raw, score):
    raw["prom_scores"][-1]["score"] = score
    assert DigaExport.model_validate(raw).prom_scores[-1].score == score


@pytest.mark.parametrize("score", [-1, 22])
def test_out_of_range_anxiety_score_is_rejected(raw, score):
    raw["prom_scores"][-1]["score"] = score
    with pytest.raises(ValidationError, match="outside 0..21"):
        DigaExport.model_validate(raw)


def test_duplicate_completion_is_rejected(raw):
    raw["prom_scores"].append(raw["prom_scores"][-1])
    with pytest.raises(ValidationError, match="duplicate prom_scores"):
        DigaExport.model_validate(raw)


@pytest.mark.parametrize("score", [True, "7", 7.0])
def test_score_must_be_a_real_integer(raw, score):
    raw["prom_scores"][-1]["score"] = score
    with pytest.raises(ValidationError):
        DigaExport.model_validate(raw)


def test_naive_completion_time_is_rejected(raw):
    raw["prom_scores"][-1]["completed_at"] = "2026-08-30T19:55:00"
    with pytest.raises(ValidationError, match="timezone"):
        DigaExport.model_validate(raw)
