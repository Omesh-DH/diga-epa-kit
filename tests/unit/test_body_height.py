import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from diga_epa_kit import DigaExport, build_bundle, check_bundle

EXAMPLE = Path(__file__).parents[2] / "synthetic" / "archetype_b_metabolic" / "weight_bmi_and_steps.json"
NOW = datetime(2026, 11, 1, 9, 0, tzinfo=timezone.utc)
PROFILE = "https://fhir.kbv.de/StructureDefinition/KBV_PR_MIO_DIGA_Observation_Body_Height|1.1.0"
SNOMED_VERSION = "http://snomed.info/sct/900000000000207008/version/20220331"


@pytest.fixture
def raw() -> dict:
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


@pytest.fixture
def bundle(raw) -> dict:
    return build_bundle(DigaExport.model_validate(raw), now=NOW)


def _heights(bundle):
    return [e["resource"] for e in bundle["entry"] if e["resource"]["meta"]["profile"] == [PROFILE]]


def test_example_passes_local_checks(bundle):
    assert check_bundle(bundle) == []


def test_body_height_shape(bundle):
    (height,) = _heights(bundle)
    patient = next(e["resource"] for e in bundle["entry"] if e["resource"]["resourceType"] == "Patient")
    assert height["status"] == "final"
    assert height["code"] == {
        "coding": [
            {"system": "http://loinc.org", "version": "2.72", "code": "8302-2", "display": "Body height"},
            {
                "system": "http://snomed.info/sct",
                "version": SNOMED_VERSION,
                "code": "1153637007",
                "display": "Body height (observable entity)",
            },
        ]
    }
    assert height["category"][0]["coding"][0]["code"] == "vital-signs"
    assert height["valueQuantity"] == {
        "value": 168.0,
        "unit": "cm",
        "system": "http://unitsofmeasure.org",
        "code": "cm",
    }
    assert height["effectiveDateTime"] == "2026-09-01T18:40:00+02:00"
    assert height["subject"] == {"reference": f"urn:uuid:{patient['id']}"}
    assert height["performer"] == [{"reference": f"urn:uuid:{patient['id']}"}]
    assert height["identifier"][0]["value"] == f"urn:uuid:{height['id']}"


def test_profile_prohibitions_are_respected(bundle):
    (height,) = _heights(bundle)
    prohibited = {
        "implicitRules", "language", "contained", "basedOn", "partOf", "encounter", "issued", "focus",
        "dataAbsentReason", "interpretation", "referenceRange", "hasMember", "derivedFrom", "specimen", "component",
    }  # fmt: skip
    assert not prohibited & set(height)
    assert "text" not in height["code"]


def test_height_sits_in_the_vitals_subsection(bundle):
    results = bundle["entry"][0]["resource"]["section"][0]
    (vitals,) = results["section"]
    (height,) = _heights(bundle)
    assert f"urn:uuid:{height['id']}" in [e["reference"] for e in vitals["entry"]]
    assert f"urn:uuid:{height['id']}" not in [e["reference"] for e in results["entry"]]


def test_height_may_predate_the_period_but_not_follow_it(raw):
    # Entered once at the start of use: older than the period is normal.
    assert raw["body_heights"][0]["measured_at"] < raw["period_start"]
    assert DigaExport.model_validate(raw).body_heights
    raw["body_heights"][0]["measured_at"] = "2026-10-26T08:00:00+01:00"
    with pytest.raises(ValidationError, match="after period_end"):
        DigaExport.model_validate(raw)


@pytest.mark.parametrize(
    "stamp",
    [
        "2026-10-21T12:00:00+02:00",  # inside the period
        "2026-10-25T23:59:00+01:00",  # last day of the period
        # 26 October in UTC, but still the 25th where it was recorded: the local date counts.
        "2026-10-25T23:30:00-05:00",
    ],
)
def test_height_up_to_the_period_end_is_accepted(raw, stamp):
    raw["body_heights"][0]["measured_at"] = stamp
    assert DigaExport.model_validate(raw).body_heights


def test_height_is_rounded_to_one_decimal(raw):
    raw["body_heights"][0]["cm"] = 168.26
    bundle = build_bundle(DigaExport.model_validate(raw), now=NOW)
    assert _heights(bundle)[0]["valueQuantity"]["value"] == 168.3


@pytest.mark.parametrize("cm", [30, 280, -1, 1.68])
def test_implausible_height_is_rejected(raw, cm):
    # 1.68 is the usual mistake of entering metres.
    raw["body_heights"][0]["cm"] = cm
    with pytest.raises(ValidationError):
        DigaExport.model_validate(raw)


def test_naive_time_is_rejected(raw):
    raw["body_heights"][0]["measured_at"] = "2026-09-01T18:40:00"
    with pytest.raises(ValidationError, match="timezone"):
        DigaExport.model_validate(raw)


def test_duplicate_height_is_rejected(raw):
    raw["body_heights"].append(raw["body_heights"][0])
    with pytest.raises(ValidationError, match="duplicate body_heights"):
        DigaExport.model_validate(raw)
