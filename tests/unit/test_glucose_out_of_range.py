"""Readings a meter or sensor showed as LO or HI: exported as below or above the device limit."""

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from conftest import package_profiles, package_resource
from diga_epa_kit import DigaExport, build_bundle, check_bundle

EXAMPLE = Path(__file__).parents[2] / "synthetic" / "archetype_b_metabolic" / "glucose_sensor_out_of_range.json"
NOW = datetime(2026, 11, 1, 9, 0, tzinfo=timezone.utc)
PROFILE_URL = "https://fhir.kbv.de/StructureDefinition/KBV_PR_MIO_DIGA_Observation_Glucose_Concentration"
BASE_URL = "https://fhir.kbv.de/StructureDefinition/KBV_PR_Base_Observation_Glucose_Concentration"
UCUM = "http://unitsofmeasure.org"
HI, METER_AFTER_HI, LO, METER_AFTER_LO = 2, 3, 5, 6  # positions in the example


@pytest.fixture
def raw() -> dict:
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


@pytest.fixture
def bundle(raw) -> dict:
    return build_bundle(DigaExport.model_validate(raw), now=NOW)


def _build(raw):
    return build_bundle(DigaExport.model_validate(raw), now=NOW)


def _readings(bundle):
    return [e["resource"] for e in bundle["entry"] if e["resource"]["meta"]["profile"] == [f"{PROFILE_URL}|1.1.0"]]


def test_example_passes_local_checks(bundle):
    assert check_bundle(bundle) == []
    assert len(_readings(bundle)) == 9


def test_hi_and_lo_are_exported_as_above_and_below_the_device_limit(bundle):
    readings = _readings(bundle)
    hi, lo = readings[HI], readings[LO]
    assert hi["valueQuantity"] == {"value": 400, "comparator": ">", "unit": "mg/dL", "system": UCUM, "code": "mg/dL"}
    assert lo["valueQuantity"] == {"value": 40, "comparator": "<", "unit": "mg/dL", "system": UCUM, "code": "mg/dL"}
    # FHIR element order: the comparator follows the value.
    assert list(hi["valueQuantity"]) == ["value", "comparator", "unit", "system", "code"]
    # In every other respect an ordinary sensor reading.
    numeric = readings[0]
    for key in ("status", "category", "code", "method", "subject", "performer"):
        assert hi[key] == numeric[key] and lo[key] == numeric[key], key
    assert not {"dataAbsentReason", "interpretation", "referenceRange"} & (set(hi) | set(lo))


def test_the_note_repeats_the_comparator_in_words(bundle):
    # A receiver that ignores the comparator would read "<40" as "40"; the note is the second signal.
    readings = _readings(bundle)
    assert readings[HI]["note"] == [{"text": "Außerhalb des Messbereichs des Geräts: über 400 mg/dL."}]
    assert readings[LO]["note"] == [{"text": "Außerhalb des Messbereichs des Geräts: unter 40 mg/dL."}]
    assert [n for n, r in enumerate(readings) if "note" in r] == [HI, LO]


def test_numeric_readings_carry_no_comparator(bundle):
    readings = _readings(bundle)
    marked = [n for n, r in enumerate(readings) if "comparator" in r["valueQuantity"]]
    assert marked == [HI, LO]
    # The finger-pricks taken right after the sensor's HI and LO are ordinary numbers.
    assert readings[METER_AFTER_HI]["valueQuantity"]["value"] == 428
    assert readings[METER_AFTER_LO]["valueQuantity"]["value"] == 46
    assert readings[METER_AFTER_LO]["effectiveDateTime"] == "2026-10-13T03:24:00+02:00"


@pytest.mark.parametrize("bad", ["LO", "HI", "low", "<", True, 1])
def test_only_below_and_above_are_accepted(raw, bad):
    raw["glucose_readings"][HI]["outside_measuring_range"] = bad
    with pytest.raises(ValidationError):
        DigaExport.model_validate(raw)


LIMITS = [
    ("below", 10, "mg/dL"), ("below", 40, "mg/dL"), ("below", 100, "mg/dL"),
    ("above", 200, "mg/dL"), ("above", 400, "mg/dL"), ("above", 900, "mg/dL"),
    ("below", 0.6, "mmol/L"), ("below", 2.2, "mmol/L"), ("below", 5.6, "mmol/L"),
    ("above", 11.1, "mmol/L"), ("above", 22.2, "mmol/L"), ("above", 50, "mmol/L"),
]  # fmt: skip


@pytest.mark.parametrize("side,limit,unit", LIMITS)
def test_plausible_device_limits_are_accepted(raw, side, limit, unit):
    raw["glucose_readings"][HI].update(outside_measuring_range=side, value=limit, unit=unit)
    reading = _readings(_build(raw))[HI]
    assert reading["valueQuantity"]["comparator"] == ("<" if side == "below" else ">")
    assert reading["valueQuantity"]["value"] == limit


SWAPPED = [("above", 40, "mg/dL"), ("below", 400, "mg/dL"), ("above", 2.2, "mmol/L"), ("below", 22.2, "mmol/L")]


@pytest.mark.parametrize("side,limit,unit", SWAPPED)
def test_a_swapped_direction_is_rejected(raw, side, limit, unit):
    # "above 40" would turn a severe low into a high.
    raw["glucose_readings"][HI].update(outside_measuring_range=side, value=limit, unit=unit)
    with pytest.raises(ValidationError, match="implausible"):
        DigaExport.model_validate(raw)


WRONG_UNIT = [("below", 40, "mmol/L"), ("below", 2.2, "mg/dL"), ("above", 400, "mmol/L"), ("above", 22.2, "mg/dL")]


@pytest.mark.parametrize("side,limit,unit", WRONG_UNIT)
def test_a_limit_in_the_wrong_unit_is_rejected(raw, side, limit, unit):
    # Unlike a plain value between 10 and 56, a device limit cannot pass in the other unit.
    raw["glucose_readings"][HI].update(outside_measuring_range=side, value=limit, unit=unit)
    with pytest.raises(ValidationError, match="implausible|outside"):
        DigaExport.model_validate(raw)


JUST_OUTSIDE = [
    ("below", 100.1, "mg/dL"),
    ("above", 199.9, "mg/dL"),
    ("below", 5.7, "mmol/L"),
    ("above", 11.0, "mmol/L"),
]


@pytest.mark.parametrize("side,limit,unit", JUST_OUTSIDE)
def test_the_limit_rule_has_exact_edges(raw, side, limit, unit):
    raw["glucose_readings"][HI].update(outside_measuring_range=side, value=limit, unit=unit)
    with pytest.raises(ValidationError, match="implausible"):
        DigaExport.model_validate(raw)


def test_a_meter_reading_can_be_out_of_range_and_keep_its_context(raw):
    raw["glucose_readings"][METER_AFTER_HI].update(value=600, outside_measuring_range="above", context="after_meal")
    meter = _readings(_build(raw))[METER_AFTER_HI]
    assert meter["valueQuantity"] == {"value": 600, "comparator": ">", "unit": "mg/dL", "system": UCUM, "code": "mg/dL"}
    assert meter["code"]["coding"][0]["code"] == "2339-0"
    assert meter["method"]["coding"][0]["code"] == "302788006"


def test_a_limit_in_mmol_is_coded_like_any_value_and_written_with_a_decimal_comma(raw):
    raw["glucose_readings"][LO].update(value=2.2, unit="mmol/L")
    lo = _readings(_build(raw))[LO]
    assert lo["valueQuantity"] == {"value": 2.2, "comparator": "<", "unit": "mmol/L", "system": UCUM, "code": "mmol/L"}
    assert lo["code"]["coding"][0]["code"] == "14745-4"
    assert lo["note"] == [{"text": "Außerhalb des Messbereichs des Geräts: unter 2,2 mmol/L."}]


@pytest.mark.parametrize("limit,unit", [(2.24, "mmol/L"), (39.95, "mg/dL")])
def test_a_limit_is_never_rounded(raw, limit, unit):
    # "<2.24" exported as "<2.2" would claim more than the device said.
    raw["glucose_readings"][LO].update(value=limit, unit=unit)
    with pytest.raises(ValidationError, match="at most one decimal"):
        DigaExport.model_validate(raw)


def test_the_field_is_about_the_device_not_the_target_range(raw):
    # Known limitation: 62 mg/dL "below" is a plausible device limit as far as any rule can
    # tell, so a caller who means "below the patient's target range" is not stopped. The
    # field name and description are the only guard (docs/mapping.md).
    raw["glucose_readings"][LO].update(value=62)
    assert _readings(_build(raw))[LO]["valueQuantity"]["comparator"] == "<"


DOUBLE_FAULT = [("above", 40, "mmol/L"), ("below", 22.2, "mg/dL")]


@pytest.mark.parametrize("side,limit,unit", DOUBLE_FAULT)
def test_a_swapped_direction_together_with_the_wrong_unit_passes(raw, side, limit, unit):
    # Known limitation: a true "below 40 mg/dL" entered as "above 40 mmol/L" needs two independent
    # mistakes, but no rule on a single reading can catch it (docs/mapping.md).
    raw["glucose_readings"][HI].update(**{"outside_measuring_range": side}, value=limit, unit=unit)
    assert DigaExport.model_validate(raw).glucose_readings[HI].value == limit


def test_marking_a_reading_out_of_range_does_not_change_its_id(raw, bundle):
    before = [r["id"] for r in _readings(bundle)]
    raw["glucose_readings"][7].update(value=40, outside_measuring_range="below")
    assert [r["id"] for r in _readings(_build(raw))] == before


def test_out_of_range_readings_share_the_duplicate_rule(raw):
    raw["glucose_readings"].append(dict(raw["glucose_readings"][LO], outside_measuring_range=None, value=41))
    with pytest.raises(ValidationError, match="duplicate glucose_readings"):
        DigaExport.model_validate(raw)


def test_the_profiles_require_a_value_forbid_absent_data_and_allow_the_comparator():
    # Why LO and HI are carried as a comparator on the device limit (docs/gaps.md G16).
    mio = package_resource("kbv.mio.diga#1.1.0", PROFILE_URL)["differential"]["element"]
    base = package_resource("kbv.basis#1.3.0", BASE_URL)["differential"]["element"]
    mio_by_id = {e["id"]: e for e in mio}
    assert mio_by_id["Observation.value[x]"]["min"] == 1
    assert mio_by_id["Observation.dataAbsentReason"]["max"] == "0"
    assert {e["id"]: e for e in base}["Observation.value[x]:valueQuantity.value"]["min"] == 1
    assert not [e["id"] for e in (*mio, *base) if "comparator" in e["id"]]


def test_the_comparator_is_prohibited_in_nine_other_observation_profiles():
    # The evidence in docs/gaps.md G16 that the rule differs between profiles.
    prohibited = set()
    for profile in package_profiles("kbv.mio.diga#1.1.0"):
        if profile.get("type") != "Observation":
            continue
        for element in profile["differential"]["element"]:
            if element["id"].endswith("valueQuantity.comparator") and element.get("max") == "0":
                prohibited.add(profile["name"].removeprefix("KBV_PR_MIO_DIGA_Observation_"))
    assert prohibited == {
        "Blood_Pressure",
        "Body_Weight",
        "Functional_Assessment",
        "Head_Circumference",
        "Heart_Rate",
        "Nutrition_Intake",
        "Nutrition_Intake_Food_Composition_Types",
        "Respiratory_Rate",
        "Score_or_Assessment_by_Scale",
    }


def test_the_other_routes_for_an_out_of_range_reading_are_closed():
    mio = {e["id"]: e for e in package_resource("kbv.mio.diga#1.1.0", PROFILE_URL)["differential"]["element"]}
    base = {e["id"]: e for e in package_resource("kbv.basis#1.3.0", BASE_URL)["differential"]["element"]}
    assert mio["Observation.extension"]["slicing"]["rules"] == "closed"
    assert mio["Observation.value[x]"]["slicing"]["rules"] == "closed"
    assert mio["Observation.referenceRange.text"]["max"] == "0"
    assert base["Observation.component"]["max"] == "0"
    binding = base["Observation.interpretation.coding"]["binding"]
    assert binding["strength"] == "required"
    trend = package_resource("kbv.basis#1.3.0", binding["valueSet"])["compose"]["include"]
    assert sum(len(inc["concept"]) for inc in trend) == 7
    # The note, used as the second signal, is must-support and may carry text only.
    assert mio["Observation.note.text"]["mustSupport"] is True
    assert mio["Observation.note.author[x]"]["max"] == mio["Observation.note.time"]["max"] == "0"
