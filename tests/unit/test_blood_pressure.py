import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from diga_epa_kit import DigaExport, build_bundle, check_bundle

EXAMPLE = Path(__file__).parents[2] / "synthetic" / "archetype_b_metabolic" / "weight_and_blood_pressure.json"
NOW = datetime(2026, 10, 1, 9, 0, tzinfo=timezone.utc)
SNOMED_VERSION = "http://snomed.info/sct/900000000000207008/version/20220331"
BP_PROFILE = "https://fhir.kbv.de/StructureDefinition/KBV_PR_MIO_DIGA_Observation_Blood_Pressure|1.1.0"


@pytest.fixture
def raw() -> dict:
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


@pytest.fixture
def bundle(raw) -> dict:
    return build_bundle(DigaExport.model_validate(raw), now=NOW)


def _bps(bundle):
    return [e["resource"] for e in bundle["entry"] if BP_PROFILE in e["resource"]["meta"]["profile"]]


def test_example_passes_local_checks(bundle):
    assert check_bundle(bundle) == []


def test_reading_lives_in_two_components(bundle):
    bp = _bps(bundle)[0]
    # The base profile prohibits Observation.value, and this profile referenceRange and interpretation.
    assert not {"valueQuantity", "referenceRange", "interpretation", "dataAbsentReason"} & bp.keys()
    systolic, diastolic = bp["component"]
    assert [c["code"] for c in systolic["code"]["coding"]] == ["8480-6", "271649006"]
    assert [c["code"] for c in diastolic["code"]["coding"]] == ["8462-4", "271650006"]
    assert systolic["valueQuantity"] == {
        "value": 148,
        "unit": "mm Hg",
        "system": "http://unitsofmeasure.org",
        "code": "mm[Hg]",
    }
    assert diastolic["valueQuantity"]["value"] == 94


def test_panel_code_and_pinned_versions(bundle):
    bp = _bps(bundle)[0]
    loinc, snomed = bp["code"]["coding"]
    assert (loinc["code"], loinc["version"]) == ("85354-9", "2.72")
    assert snomed["code"] == "75367002"
    codings = [loinc, snomed] + [c for comp in bp["component"] for c in comp["code"]["coding"]]
    # Pattern values of kbv.basis KBV_PR_Base_Observation_Blood_Pressure (loinc.display, codeSnomed).
    assert [c["display"] for c in codings] == [
        "Blood pressure panel with all children optional",
        "Blood pressure (observable entity)",
        "Systolic blood pressure",
        "Systolic blood pressure (observable entity)",
        "Diastolic blood pressure",
        "Diastolic blood pressure (observable entity)",
    ]
    assert [c["version"] for c in codings] == ["2.72", SNOMED_VERSION] * 3


def test_subject_performer_and_local_offset(bundle):
    bp = _bps(bundle)[0]
    patient = next(e["resource"] for e in bundle["entry"] if e["resource"]["resourceType"] == "Patient")
    ref = {"reference": f"urn:uuid:{patient['id']}"}
    assert bp["subject"] == ref and bp["performer"] == [ref]
    assert bp["effectiveDateTime"] == "2026-09-01T07:35:00+02:00"


def test_vital_signs_section_lists_weights_then_blood_pressures(raw, bundle):
    (results,) = bundle["entry"][0]["resource"]["section"]
    (vitals,) = results["section"]
    refs = [e["reference"] for e in vitals["entry"]]
    assert len(refs) == len(raw["body_weights"]) + len(raw["blood_pressures"])
    assert refs[len(raw["body_weights"]) :] == [f"urn:uuid:{b['id']}" for b in _bps(bundle)]


@pytest.mark.parametrize(
    "patch, match",
    [
        ({"systolic": 120, "diastolic": 120}, "diastolic must be below systolic"),
        ({"systolic": 301}, "300"),
        ({"systolic": 39, "diastolic": 30}, "40"),
        ({"diastolic": 19}, "20"),
        ({"systolic": 250, "diastolic": 201}, "200"),
        ({"systolic": 120.5}, "int"),
        ({"measured_at": "2026-09-01T07:35:00"}, "timezone"),
        ({"measured_at": "2026-10-01T07:35:00+02:00"}, "outside period"),
    ],
)
def test_bad_reading_is_rejected(raw, patch, match):
    raw["blood_pressures"][0].update(patch)
    with pytest.raises(ValidationError, match=match):
        DigaExport.model_validate(raw)


def test_duplicate_reading_is_rejected(raw):
    raw["blood_pressures"].append(raw["blood_pressures"][0])
    with pytest.raises(ValidationError, match="duplicate blood_pressures"):
        DigaExport.model_validate(raw)
