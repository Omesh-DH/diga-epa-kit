import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from diga_epa_kit import DigaExport, build_bundle, check_bundle

EXAMPLE = Path(__file__).parents[2] / "synthetic" / "archetype_b_metabolic" / "home_vital_signs.json"
NOW = datetime(2026, 11, 9, 9, 0, tzinfo=timezone.utc)
SD = "https://fhir.kbv.de/StructureDefinition/KBV_PR_MIO_DIGA_Observation_"
SNOMED_VERSION = "http://snomed.info/sct/900000000000207008/version/20220331"

# profile suffix, input list, value field, LOINC, SNOMED, unit text, UCUM code, first value
CASES = [
    ("Heart_Rate", "heart_rates", "bpm", ("8867-4", "Heart rate"),
     ("364075005", "Heart rate (observable entity)"), "per minute", "/min", 74),
    ("Body_Temperature", "body_temperatures", "celsius", ("8310-5", "Body temperature"),
     ("386725007", "Body temperature (observable entity)"), "Celsius", "Cel", 36.6),
    ("Peripheral_Oxygen_Saturation", "oxygen_saturations", "percent", ("2708-6", "Oxygen saturation in Arterial blood"),
     ("431314004", "Peripheral oxygen saturation (observable entity)"), "%", "%", 97),
    ("Respiratory_Rate", "respiratory_rates", "per_minute", ("9279-1", "Respiratory rate"),
     ("86290005", "Respiratory rate (observable entity)"), "per minute", "/min", 15),
]  # fmt: skip
IDS = [c[0] for c in CASES]


@pytest.fixture
def raw() -> dict:
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


@pytest.fixture
def bundle(raw) -> dict:
    return build_bundle(DigaExport.model_validate(raw), now=NOW)


def _of(bundle, suffix):
    return [e["resource"] for e in bundle["entry"] if e["resource"]["meta"]["profile"] == [f"{SD}{suffix}|1.1.0"]]


def test_example_passes_local_checks(bundle):
    assert check_bundle(bundle) == []


@pytest.mark.parametrize("suffix,field,_v,loinc,snomed,unit,ucum,first", CASES, ids=IDS)
def test_shape(raw, bundle, suffix, field, _v, loinc, snomed, unit, ucum, first):
    found = _of(bundle, suffix)
    assert len(found) == len(raw[field])
    obs = found[0]
    patient = next(e["resource"] for e in bundle["entry"] if e["resource"]["resourceType"] == "Patient")
    assert obs["status"] == "final"
    assert obs["category"] == [
        {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "vital-signs"}]}
    ]
    assert obs["code"] == {
        "coding": [
            {"system": "http://loinc.org", "version": "2.72", "code": loinc[0], "display": loinc[1]},
            {"system": "http://snomed.info/sct", "version": SNOMED_VERSION, "code": snomed[0], "display": snomed[1]},
        ]
    }
    assert obs["valueQuantity"] == {"value": first, "unit": unit, "system": "http://unitsofmeasure.org", "code": ucum}
    assert obs["effectiveDateTime"] == raw[field][0]["measured_at"]
    assert obs["subject"] == {"reference": f"urn:uuid:{patient['id']}"}
    assert obs["performer"] == [{"reference": f"urn:uuid:{patient['id']}"}]
    assert obs["identifier"][0]["value"] == f"urn:uuid:{obs['id']}"
    prohibited = {
        "implicitRules", "language", "contained", "basedOn", "partOf", "encounter", "issued", "focus",
        "dataAbsentReason", "interpretation", "referenceRange", "hasMember", "derivedFrom", "specimen", "component",
    }  # fmt: skip
    assert not prohibited & set(obs)


def test_only_oxygen_saturation_carries_a_method(bundle):
    # kbv.basis requires and fixes the pulse oximeter there; the other three have no method value set.
    (spo2, _) = _of(bundle, "Peripheral_Oxygen_Saturation")
    assert spo2["method"] == {
        "coding": [
            {
                "system": "http://snomed.info/sct",
                "version": SNOMED_VERSION,
                "code": "448703006",
                "display": "Pulse oximeter (physical object)",
            }
        ]
    }
    for suffix in ("Heart_Rate", "Body_Temperature", "Respiratory_Rate"):
        assert all("method" not in o for o in _of(bundle, suffix))


def test_all_readings_sit_in_the_vitals_subsection_in_a_fixed_order(bundle):
    (results,) = bundle["entry"][0]["resource"]["section"]
    assert "entry" not in results
    (vitals,) = results["section"]
    by_url = {e["fullUrl"]: e["resource"] for e in bundle["entry"]}
    kinds = [
        by_url[e["reference"]]["meta"]["profile"][0].split("Observation_")[1].split("|")[0] for e in vitals["entry"]
    ]
    assert kinds == (
        ["Blood_Pressure"] * 2
        + ["Heart_Rate"] * 3
        + ["Body_Temperature"] * 2
        + ["Peripheral_Oxygen_Saturation"] * 2
        + ["Respiratory_Rate"] * 2
    )
    ids = [e["resource"]["id"] for e in bundle["entry"]]
    assert len(set(ids)) == len(ids)


def test_same_minute_readings_of_different_kinds_do_not_collide(raw):
    stamp = "2026-10-14T08:00:00+02:00"
    for field in ("blood_pressures", "heart_rates", "body_temperatures", "oxygen_saturations", "respiratory_rates"):
        raw[field][0]["measured_at"] = stamp
    bundle = build_bundle(DigaExport.model_validate(raw), now=NOW)
    ids = [e["resource"]["id"] for e in bundle["entry"]]
    assert len(set(ids)) == len(ids)


def test_temperature_is_rounded_to_one_decimal(raw):
    raw["body_temperatures"][0]["celsius"] = 36.66
    bundle = build_bundle(DigaExport.model_validate(raw), now=NOW)
    assert _of(bundle, "Body_Temperature")[0]["valueQuantity"]["value"] == 36.7


BOUNDS = [("heart_rates", "bpm", 20, 300), ("body_temperatures", "celsius", 25, 45),
          ("oxygen_saturations", "percent", 50, 100), ("respiratory_rates", "per_minute", 4, 80)]  # fmt: skip


@pytest.mark.parametrize("field,key,low,high", BOUNDS, ids=[b[0] for b in BOUNDS])
def test_bounds(raw, field, key, low, high):
    for ok in (low, high):
        raw[field][0][key] = ok
        DigaExport.model_validate(raw)
    for bad in (low - 1, high + 1):
        raw[field][0][key] = bad
        with pytest.raises(ValidationError):
            DigaExport.model_validate(raw)


@pytest.mark.parametrize(
    "field,key", [("heart_rates", "bpm"), ("oxygen_saturations", "percent"), ("respiratory_rates", "per_minute")]
)
def test_counts_must_be_whole_numbers(raw, field, key):
    for bad in (72.5, "72", True):
        raw[field][0][key] = bad
        with pytest.raises(ValidationError):
            DigaExport.model_validate(raw)


@pytest.mark.parametrize("bad", ["36.6", True])
def test_temperature_must_be_a_number(raw, bad):
    raw["body_temperatures"][0]["celsius"] = bad
    with pytest.raises(ValidationError):
        DigaExport.model_validate(raw)


def test_whole_degrees_are_accepted(raw):
    raw["body_temperatures"][0]["celsius"] = 37
    bundle = build_bundle(DigaExport.model_validate(raw), now=NOW)
    assert _of(bundle, "Body_Temperature")[0]["valueQuantity"]["value"] == 37


def test_example_lies_before_the_export_date_of_the_golden_bundles(raw):
    assert raw["period_end"] < "2026-11-01"


@pytest.mark.parametrize("field", [b[0] for b in BOUNDS])
def test_time_rules(raw, field):
    first = dict(raw[field][0])
    raw[field][0] = {**first, "measured_at": "2026-10-14T08:00:00"}
    with pytest.raises(ValidationError, match="timezone"):
        DigaExport.model_validate(raw)
    raw[field][0] = {**first, "measured_at": "2026-10-19T08:00:00+02:00"}
    with pytest.raises(ValidationError, match="outside period"):
        DigaExport.model_validate(raw)
    raw[field][0] = first
    raw[field].append(first)
    with pytest.raises(ValidationError, match=f"duplicate {field}"):
        DigaExport.model_validate(raw)
