import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from diga_epa_kit import DigaExport, build_bundle, check_bundle
from diga_epa_kit.terminology.instruments import INSTRUMENTS, PAIN_NRS

EXAMPLE = Path(__file__).parents[2] / "synthetic" / "archetype_c_pain" / "pain_scale_and_diary.json"
NOW = datetime(2026, 11, 1, 9, 0, tzinfo=timezone.utc)
SCORE_PROFILE = "https://fhir.kbv.de/StructureDefinition/KBV_PR_MIO_DIGA_Observation_Score_or_Assessment_by_Scale|1.1.0"


@pytest.fixture
def raw() -> dict:
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


@pytest.fixture
def bundle(raw) -> dict:
    return build_bundle(DigaExport.model_validate(raw), now=NOW)


def _scores(bundle):
    return [e["resource"] for e in bundle["entry"] if SCORE_PROFILE in e["resource"]["meta"]["profile"]]


def test_example_passes_local_checks(bundle):
    assert check_bundle(bundle) == []


def test_pain_score_shape(bundle):
    scores = _scores(bundle)
    assert [s["valueQuantity"]["value"] for s in scores] == [7, 6, 6, 4, 3]
    first = scores[0]
    assert first["code"] == {
        "coding": [
            {
                "system": "http://loinc.org",
                "version": "2.72",
                "code": "72514-3",
                "display": "Pain severity - 0-10 verbal numeric rating [Score] - Reported",
            }
        ]
    }
    (rr,) = first["referenceRange"]
    assert (rr["low"]["value"], rr["high"]["value"]) == (PAIN_NRS.min_score, PAIN_NRS.max_score) == (0, 10)
    assert "text" not in rr
    assert first["valueQuantity"]["code"] == "{score}"
    assert first["category"][0]["coding"][0]["code"] == "survey"
    patient = next(e["resource"] for e in bundle["entry"] if e["resource"]["resourceType"] == "Patient")
    device = next(e["resource"] for e in bundle["entry"] if e["resource"]["resourceType"] == "Device")
    assert first["performer"] == [{"reference": f"urn:uuid:{patient['id']}"}]
    assert first["device"] == {"reference": f"urn:uuid:{device['id']}"}


@pytest.mark.parametrize("score", [0, 10])
def test_scale_ends_are_accepted(raw, score):
    raw["prom_scores"][0]["score"] = score
    assert DigaExport.model_validate(raw).prom_scores[0].score == score


def test_fractional_pain_score_is_rejected(raw):
    raw["prom_scores"][0]["score"] = 6.5
    with pytest.raises(ValidationError):
        DigaExport.model_validate(raw)


def test_duplicate_rating_is_rejected(raw):
    raw["prom_scores"].append(raw["prom_scores"][0])
    with pytest.raises(ValidationError, match="duplicate prom_scores"):
        DigaExport.model_validate(raw)


def test_local_offset_survives_the_clock_change(bundle):
    assert _scores(bundle)[-1]["effectiveDateTime"] == "2026-10-30T08:15:00+01:00"


def test_sections_are_assessments_then_reports(bundle):
    assessments, reports = bundle["entry"][0]["resource"]["section"]
    assert (assessments["title"], reports["title"]) == ("Beurteilungen", "Patientenberichte")
    assert len(assessments["entry"]) == 5 and len(reports["entry"]) == 3


@pytest.mark.parametrize("score", [-1, 11])
def test_out_of_range_pain_score_is_rejected(raw, score):
    raw["prom_scores"][0]["score"] = score
    with pytest.raises(ValidationError, match="outside 0..10"):
        DigaExport.model_validate(raw)


def test_two_instruments_at_the_same_time_are_allowed(raw):
    raw["prom_scores"].append({"instrument": "phq9", "completed_at": "2026-10-02T08:10:00+02:00", "score": 5})
    bundle = build_bundle(DigaExport.model_validate(raw), now=NOW)
    codes = [s["code"]["coding"][0]["code"] for s in _scores(bundle)]
    assert codes.count("72514-3") == 5 and codes.count("44261-6") == 1
    assert len({s["id"] for s in _scores(bundle)}) == 6


def test_unknown_instrument_is_rejected(raw):
    raw["prom_scores"][0]["instrument"] = "odi"
    with pytest.raises(ValidationError, match="instrument"):
        DigaExport.model_validate(raw)


def test_every_catalogue_entry_is_accepted_by_the_input_model():
    from typing import get_args

    from diga_epa_kit.input.model import PromScore

    assert set(get_args(PromScore.model_fields["instrument"].annotation)) == set(INSTRUMENTS)
