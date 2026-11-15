import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from conftest import package_resource
from diga_epa_kit import DigaExport, build_bundle, check_bundle
from diga_epa_kit.mappers import vitals

EXAMPLE = Path(__file__).parents[2] / "synthetic" / "archetype_b_metabolic" / "glucose_diary.json"
NOW = datetime(2026, 11, 1, 9, 0, tzinfo=timezone.utc)
PROFILE_URL = "https://fhir.kbv.de/StructureDefinition/KBV_PR_MIO_DIGA_Observation_Glucose_Concentration"
PROFILE = f"{PROFILE_URL}|1.1.0"
SNOMED_VERSION = "http://snomed.info/sct/900000000000207008/version/20220331"
CONTEXTS = ["fasting", "before_lunch", "before_supper", "before_bed", "after_meal", "random"]


@pytest.fixture
def raw() -> dict:
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


@pytest.fixture
def bundle(raw) -> dict:
    return build_bundle(DigaExport.model_validate(raw), now=NOW)


def _readings(bundle):
    return [e["resource"] for e in bundle["entry"] if e["resource"]["meta"]["profile"] == [PROFILE]]


def _method_code(reading):
    return reading["method"]["coding"][0]["code"] if "method" in reading else None


def test_example_passes_local_checks(bundle):
    assert check_bundle(bundle) == []


def test_fasting_blood_reading_shape(bundle):
    first = _readings(bundle)[0]
    patient = next(e["resource"] for e in bundle["entry"] if e["resource"]["resourceType"] == "Patient")
    assert first["status"] == "final"
    assert first["category"][0]["coding"][0]["code"] == "vital-signs"
    assert first["code"] == {
        "coding": [
            {
                "system": "http://loinc.org",
                "version": "2.72",
                "code": "2339-0",
                "display": "Glucose [Mass/volume] in Blood",
            },
            {
                "system": "http://snomed.info/sct",
                "version": SNOMED_VERSION,
                "code": "434912009",
                "display": "Blood glucose concentration (observable entity)",
            },
        ]
    }
    assert first["valueQuantity"] == {
        "value": 128,
        "unit": "mg/dL",
        "system": "http://unitsofmeasure.org",
        "code": "mg/dL",
    }
    assert first["method"] == {
        "coding": [
            {
                "system": "http://snomed.info/sct",
                "version": SNOMED_VERSION,
                "code": "271062006",
                "display": "Fasting blood glucose measurement (procedure)",
            }
        ]
    }
    assert first["effectiveDateTime"] == "2026-10-05T07:05:00+02:00"
    assert first["subject"] == {"reference": f"urn:uuid:{patient['id']}"}
    assert first["performer"] == [{"reference": f"urn:uuid:{patient['id']}"}]
    assert first["identifier"][0]["value"] == f"urn:uuid:{first['id']}"


def test_code_follows_specimen_and_unit(bundle):
    codes = [tuple(c["code"] for c in r["code"]["coding"]) for r in _readings(bundle)]
    assert codes[:6] == [("2339-0", "434912009")] * 6  # blood, mg/dL
    assert codes[6] == ("15074-8", "434912009")  # blood, mmol/L
    assert codes[7] == ("14745-4", "434910001")  # interstitial fluid, mmol/L
    assert codes[8] == ("2344-0", "434910001")  # interstitial fluid, mg/dL
    displays = {c["code"]: c["display"] for r in _readings(bundle) for c in r["code"]["coding"]}
    assert displays["15074-8"] == "Glucose [Moles/volume] in Blood"
    assert displays["14745-4"] == "Glucose [Moles/volume] in Body fluid"
    assert displays["2344-0"] == "Glucose [Mass/volume] in Body fluid"
    assert displays["434910001"] == "Interstitial fluid glucose concentration (observable entity)"
    assert _readings(bundle)[6]["valueQuantity"] == {
        "value": 6.9,
        "unit": "mmol/L",
        "system": "http://unitsofmeasure.org",
        "code": "mmol/L",
    }


def test_method_follows_the_context_for_blood_and_is_cgm_for_sensor_readings(bundle):
    readings = _readings(bundle)
    assert [_method_code(r) for r in readings] == [
        "271062006",  # fasting
        "302788006",  # after_meal
        "271063001",  # before_lunch
        "271064007",  # before_supper
        "271065008",  # before_bed
        "271061004",  # random
        None,  # blood without a context
        "359776002",  # sensor
        "359776002",  # sensor
    ]
    assert "method" not in readings[6]
    assert readings[7]["method"] == {
        "coding": [
            {
                "system": "http://snomed.info/sct",
                "version": SNOMED_VERSION,
                "code": "359776002",
                "display": "Glucose measurement by monitoring device (procedure)",
            }
        ]
    }


def test_meter_and_sensor_in_the_same_minute_are_two_readings(raw, bundle):
    meter, sensor = _readings(bundle)[6], _readings(bundle)[7]
    assert meter["effectiveDateTime"] == sensor["effectiveDateTime"] == "2026-10-10T07:10:00+02:00"
    assert meter["id"] != sensor["id"]
    ids = [e["resource"]["id"] for e in bundle["entry"]]
    assert len(set(ids)) == len(ids)
    # The same specimen twice at one time is still a duplicate.
    raw["glucose_readings"].append(dict(raw["glucose_readings"][7]))
    with pytest.raises(ValidationError, match="duplicate glucose_readings"):
        DigaExport.model_validate(raw)


def test_profile_prohibitions_are_respected(bundle):
    prohibited = {
        "implicitRules", "language", "contained", "basedOn", "partOf", "focus", "encounter", "issued",
        "dataAbsentReason", "specimen", "hasMember", "derivedFrom", "component",
    }  # fmt: skip
    for r in _readings(bundle):
        assert not prohibited & set(r)
        assert "text" not in r["code"]
        assert "text" not in r.get("method", {})
        assert "comparator" not in r["valueQuantity"]
        # Not exported: the input has neither a trend nor a target range.
        assert "interpretation" not in r and "referenceRange" not in r


def test_readings_sit_in_the_vitals_subsection(bundle):
    (results,) = bundle["entry"][0]["resource"]["section"]
    (vitals_section,) = results["section"]
    assert [e["reference"] for e in vitals_section["entry"]] == [f"urn:uuid:{r['id']}" for r in _readings(bundle)]


BOUNDS = [("mg/dL", 10, 1000), ("mmol/L", 0.5, 56)]


@pytest.mark.parametrize("unit,low,high", BOUNDS)
def test_bounds_per_unit(raw, unit, low, high):
    reading = raw["glucose_readings"][0]
    reading["unit"] = unit
    for ok in (low, high):
        reading["value"] = ok
        DigaExport.model_validate(raw)
    for bad in (low - 0.1, high + 0.1):
        reading["value"] = bad
        with pytest.raises(ValidationError, match="outside"):
            DigaExport.model_validate(raw)


@pytest.mark.parametrize("value", [10, 12, 45, 56])
def test_a_wrong_unit_passes_inside_the_overlap_of_the_two_ranges(raw, value):
    # 12 mmol/L (high) labelled mg/dL, or 45 mg/dL (low) labelled mmol/L, looks like a correct
    # reading: the kit exports what it is given (docs/mapping.md, "Units").
    for unit in ("mg/dL", "mmol/L"):
        raw["glucose_readings"][0].update(value=value, unit=unit)
        assert DigaExport.model_validate(raw).glucose_readings[0].value == value


@pytest.mark.parametrize("value,unit", [(7, "mg/dL"), (9.9, "mg/dL"), (126, "mmol/L"), (56.1, "mmol/L")])
def test_a_wrong_unit_is_caught_outside_the_overlap(raw, value, unit):
    raw["glucose_readings"][0].update(value=value, unit=unit)
    with pytest.raises(ValidationError, match="outside"):
        DigaExport.model_validate(raw)


@pytest.mark.parametrize("bad", ["128", True, None, float("nan"), float("inf"), float("-inf")])
def test_value_must_be_a_finite_number(raw, bad):
    raw["glucose_readings"][0]["value"] = bad
    with pytest.raises(ValidationError):
        DigaExport.model_validate(raw)


@pytest.mark.parametrize(
    "field,bad",
    [
        ("unit", "mg/dl"),
        ("unit", "g/L"),
        ("specimen", "urine"),
        ("context", "breakfast"),
        # Names that do not say "before" are not accepted: the codes mean before the meal.
        ("context", "lunch"),
        # The sensor method follows from the specimen and is never chosen by the caller.
        ("context", "monitoring_device"),
    ],
)
def test_unknown_choices_are_rejected(raw, field, bad):
    raw["glucose_readings"][0][field] = bad
    with pytest.raises(ValidationError):
        DigaExport.model_validate(raw)


def test_unit_and_specimen_are_required(raw):
    for field in ("unit", "specimen"):
        reading = dict(raw["glucose_readings"][0])
        del reading[field]
        with pytest.raises(ValidationError):
            DigaExport.model_validate({**raw, "glucose_readings": [reading]})


@pytest.mark.parametrize("context", CONTEXTS)
def test_context_applies_to_blood_only(raw, context):
    raw["glucose_readings"][8]["context"] = context
    with pytest.raises(ValidationError, match="blood readings only"):
        DigaExport.model_validate(raw)


def test_value_is_rounded_to_one_decimal(raw):
    raw["glucose_readings"][6]["value"] = 6.94
    bundle = build_bundle(DigaExport.model_validate(raw), now=NOW)
    assert _readings(bundle)[6]["valueQuantity"]["value"] == 6.9


def test_time_rules(raw):
    first = dict(raw["glucose_readings"][0])
    raw["glucose_readings"][0] = {**first, "measured_at": "2026-10-05T07:05:00"}
    with pytest.raises(ValidationError, match="timezone"):
        DigaExport.model_validate(raw)
    raw["glucose_readings"][0] = {**first, "measured_at": "2026-10-12T07:05:00+02:00"}
    with pytest.raises(ValidationError, match="outside period"):
        DigaExport.model_validate(raw)
    raw["glucose_readings"][0] = first
    raw["glucose_readings"].append(first)
    with pytest.raises(ValidationError, match="duplicate glucose_readings"):
        DigaExport.model_validate(raw)


# --- Against the pinned packages. The offline gate cannot check the value-set bindings (it only
# warns), so these tests are the check. They are skipped where the packages are not fetched.

BASIS = "kbv.basis#1.3.0"
VALUE_SET = "https://fhir.kbv.de/ValueSet/KBV_VS_Base_Glucose_Concentration_"
CONCEPT_MAP = "https://fhir.kbv.de/ConceptMap/KBV_CM_Base_Terminology_Complete_German"
GERMAN = "https://fhir.kbv.de/CodeSystem/KBV_CS_Base_Glucose_Concentration_"


def _concepts(name):
    compose = package_resource(BASIS, VALUE_SET + name)["compose"]
    return {(c["code"], c["display"]) for inc in compose["include"] for c in inc["concept"]}


def _german(target):
    """Source code -> German target code, from the concept-map group with this target."""
    (group,) = [g for g in package_resource(BASIS, CONCEPT_MAP)["group"] if g["target"] == GERMAN + target]
    return {el["code"]: el["target"][0]["code"] for el in group["element"]}


def test_every_code_the_mapper_can_emit_is_in_the_package_value_sets():
    assert set(vitals._GLUCOSE_LOINC.values()) == _concepts("LOINC")
    assert set(vitals._GLUCOSE_SNOMED.values()) == _concepts("SNOMED_CT")
    assert {*vitals._GLUCOSE_METHOD.values(), vitals._GLUCOSE_CGM} == _concepts("Method_SNOMED_CT")
    assert {code for code, _ in _concepts("Unit")} == {unit for _, unit in vitals._GLUCOSE_LOINC}


def test_loinc_and_snomed_are_paired_as_the_package_concept_map_pairs_them():
    loinc, snomed = _german("LOINC_German"), _german("SNOMED_CT_German")
    for (specimen, _unit), (code, _display) in vitals._GLUCOSE_LOINC.items():
        assert loinc[code] == snomed[vitals._GLUCOSE_SNOMED[specimen][0]], (specimen, code)
    assert len(set(snomed.values())) == 2


def test_context_names_carry_the_meaning_the_concept_map_gives_the_method_codes():
    german = _german("Method_SNOMED_CT_German")
    assert set(vitals._GLUCOSE_METHOD) == set(CONTEXTS)
    assert german[vitals._GLUCOSE_CGM[0]] == "KontinuierlicheGlukosemessungCGM"
    for context in ("before_lunch", "before_supper", "before_bed"):
        assert "vordem" in german[vitals._GLUCOSE_METHOD[context][0]]
    assert german[vitals._GLUCOSE_METHOD["after_meal"][0]].endswith("nachdemEssen")
    assert german[vitals._GLUCOSE_METHOD["fasting"][0]].endswith("nuechtern")
    assert german[vitals._GLUCOSE_METHOD["random"][0]].endswith("zufaellig")


def test_method_version_is_the_one_the_profile_pattern_fixes(bundle):
    profile = package_resource("kbv.mio.diga#1.1.0", PROFILE_URL)
    (method_slice,) = [
        e for e in profile["differential"]["element"] if e["id"] == "Observation.method.coding:codeSnomed"
    ]
    versions = {r["method"]["coding"][0]["version"] for r in _readings(bundle) if "method" in r}
    assert versions == {method_slice["patternCoding"]["version"]}
