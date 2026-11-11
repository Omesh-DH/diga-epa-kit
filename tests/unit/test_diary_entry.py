import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from diga_epa_kit import DigaExport, build_bundle, check_bundle

EXAMPLE = Path(__file__).parents[2] / "synthetic" / "archetype_a_mental" / "phq9_and_mood_diary.json"
NOW = datetime(2026, 9, 1, 9, 0, tzinfo=timezone.utc)
PROFILE = "https://fhir.kbv.de/StructureDefinition/KBV_PR_MIO_DIGA_Observation_Diary_Entry|1.1.0"


@pytest.fixture
def raw() -> dict:
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


@pytest.fixture
def bundle(raw) -> dict:
    return build_bundle(DigaExport.model_validate(raw), now=NOW)


def _diary(bundle):
    return [e["resource"] for e in bundle["entry"] if PROFILE in e["resource"]["meta"]["profile"]]


def test_example_passes_local_checks(bundle):
    assert check_bundle(bundle) == []


def test_entry_shape(raw, bundle):
    entry = _diary(bundle)[0]
    # Pattern of Observation.code in the profile.
    assert entry["code"] == {
        "coding": [{"system": "http://loinc.org", "version": "2.72", "code": "51855-5", "display": "Patient Note"}]
    }
    assert entry["status"] == "final"
    assert entry["valueString"] == raw["diary_entries"][0]["text"]
    assert entry["effectiveDateTime"] == "2026-08-04T21:30:00+02:00"
    patient = next(e["resource"] for e in bundle["entry"] if e["resource"]["resourceType"] == "Patient")
    ref = {"reference": f"urn:uuid:{patient['id']}"}
    assert entry["subject"] == ref and entry["performer"] == [ref]


def test_prohibited_elements_are_absent(bundle):
    prohibited = {"category", "method", "device", "bodySite", "component", "referenceRange", "interpretation"}
    prohibited |= {"derivedFrom", "issued", "dataAbsentReason", "basedOn", "partOf", "encounter", "focus"}
    prohibited |= {"specimen", "contained", "language", "implicitRules"}
    assert all(not prohibited & entry.keys() for entry in _diary(bundle))


def test_text_is_exported_verbatim_including_line_breaks(raw, bundle):
    assert [e["valueString"] for e in _diary(bundle)] == [d["text"] for d in raw["diary_entries"]]
    assert "\n" in _diary(bundle)[2]["valueString"]


def test_patient_reports_section_follows_assessments(bundle):
    assessments, reports = bundle["entry"][0]["resource"]["section"]
    assert assessments["title"] == "Beurteilungen"
    assert reports["title"] == "Patientenberichte"
    assert reports["code"] == {
        "coding": [
            {
                "system": "https://fhir.kbv.de/CodeSystem/KBV_CS_MIO_DIGA_Section_Codes",
                "version": "1.1.0",
                "code": "SectionPatientenberichte",
                "display": "Bereich Patientenberichte",
            }
        ]
    }
    assert [e["reference"] for e in reports["entry"]] == [f"urn:uuid:{d['id']}" for d in _diary(bundle)]


def test_no_section_without_entries(raw):
    raw["diary_entries"] = []
    bundle = build_bundle(DigaExport.model_validate(raw), now=NOW)
    assert [s["title"] for s in bundle["entry"][0]["resource"]["section"]] == ["Beurteilungen"]


@pytest.mark.parametrize(
    "patch, match",
    [
        ({"text": ""}, "at least 1"),
        ({"text": "   "}, "blank or padded"),
        ({"text": " padded"}, "blank or padded"),
        ({"text": "padded\n"}, "blank or padded"),
        ({"text": "a\x00b"}, "control characters"),
        ({"text": "a\x07b"}, "control characters"),
        ({"text": "\u200b"}, "no visible character"),
        ({"text": "x" * 5001}, "5000"),
        ({"written_at": "2026-08-04T21:30:00"}, "timezone"),
        ({"written_at": "2026-09-01T08:00:00+02:00"}, "outside period"),
    ],
)
def test_bad_entry_is_rejected(raw, patch, match):
    raw["diary_entries"][0].update(patch)
    with pytest.raises(ValidationError, match=match):
        DigaExport.model_validate(raw)


def test_longest_allowed_text_is_accepted(raw):
    raw["diary_entries"][0]["text"] = "x" * 5000
    assert len(DigaExport.model_validate(raw).diary_entries[0].text) == 5000


def test_sections_keep_profile_order_with_vitals(raw):
    raw["body_weights"] = [{"measured_at": "2026-08-05T07:00:00+02:00", "kg": 70}]
    bundle = build_bundle(DigaExport.model_validate(raw), now=NOW)
    titles = [s["title"] for s in bundle["entry"][0]["resource"]["section"]]
    assert titles == ["Befunde und Ergebnisse", "Beurteilungen", "Patientenberichte"]


def test_duplicate_entry_is_rejected(raw):
    raw["diary_entries"].append(raw["diary_entries"][0])
    with pytest.raises(ValidationError, match="duplicate diary_entries"):
        DigaExport.model_validate(raw)
