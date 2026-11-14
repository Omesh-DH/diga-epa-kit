import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from diga_epa_kit import DigaExport, build_bundle, check_bundle
from diga_epa_kit.cli import main

EXAMPLE = Path(__file__).parents[2] / "synthetic" / "archetype_b_metabolic" / "weight_one_month.json"
NOW = datetime(2026, 10, 1, 9, 0, tzinfo=timezone.utc)


@pytest.fixture
def data() -> DigaExport:
    return DigaExport.model_validate_json(EXAMPLE.read_text(encoding="utf-8"))


def _by_type(bundle, rtype):
    return [e["resource"] for e in bundle["entry"] if e["resource"]["resourceType"] == rtype]


def test_example_passes_local_checks(data):
    assert check_bundle(build_bundle(data, now=NOW)) == []


def test_build_is_deterministic(data):
    assert build_bundle(data, now=NOW) == build_bundle(data, now=NOW)


def test_composition_first_and_lists_every_weight(data):
    bundle = build_bundle(data, now=NOW)
    comp = bundle["entry"][0]["resource"]
    assert comp["resourceType"] == "Composition"
    vitals = comp["section"][0]["section"][0]
    weights = _by_type(bundle, "Observation")
    assert len(weights) == len(data.body_weights)
    assert [e["reference"] for e in vitals["entry"]] == [f"urn:uuid:{w['id']}" for w in weights]


def test_every_profile_is_versioned(data):
    bundle = build_bundle(data, now=NOW)
    for e in bundle["entry"]:
        (profile,) = e["resource"]["meta"]["profile"]
        assert profile.endswith("|1.1.0")


def test_device_carries_ve_id_and_pzn(data):
    (device,) = _by_type(build_bundle(data, now=NOW), "Device")
    assert device["identifier"] == [{"type": {"text": "DiGA-VE-ID"}, "value": "99990001"}]
    assert device["type"]["coding"][0]["code"] == "19999999"


def test_device_carries_the_software_version(data):
    (device,) = _by_type(build_bundle(data, now=NOW), "Device")
    # type is required; no coding, because the packages name no code for it.
    assert device["version"] == [{"type": {"text": "Softwareversion"}, "value": "2.4.1"}]
    (definition,) = _by_type(build_bundle(data, now=NOW), "DeviceDefinition")
    assert "version" not in definition  # max=0 in DeviceDefinition_DIGA


def test_version_is_optional_and_does_not_change_ids(data):
    without = data.model_copy(update={"diga": data.diga.model_copy(update={"version": None})})
    with_v, no_v = build_bundle(data, now=NOW), build_bundle(without, now=NOW)
    (device,) = _by_type(no_v, "Device")
    assert "version" not in device
    assert check_bundle(no_v) == []
    # An app update must not turn the same DiGA into a new device or document.
    assert [e["fullUrl"] for e in with_v["entry"]] == [e["fullUrl"] for e in no_v["entry"]]
    updated = data.model_copy(update={"diga": data.diga.model_copy(update={"version": "2.5.0"})})
    new_v = build_bundle(updated, now=NOW)
    assert [e["fullUrl"] for e in with_v["entry"]] == [e["fullUrl"] for e in new_v["entry"]]
    assert _by_type(new_v, "Device")[0]["version"][0]["value"] == "2.5.0"


@pytest.mark.parametrize("version", ["1", "2.4.1", "2.4.1-beta.3", "2024.11+build7", "v3"])
def test_usual_version_labels_are_accepted(data, version):
    raw = data.model_dump(mode="json")
    raw["diga"]["version"] = version
    assert DigaExport.model_validate(raw).diga.version == version


@pytest.mark.parametrize("version", ["", " 2.4.1", "2.4.1 ", "2.4 beta", "2.4.1 (57)", ".1", "1" * 41, "2.4\n1", "2.4.1\n", 2.4])
def test_malformed_version_is_rejected(data, version):
    raw = data.model_dump(mode="json")
    raw["diga"]["version"] = version
    with pytest.raises(ValidationError):
        DigaExport.model_validate(raw)


def test_empty_export_omits_results_section(data):
    bundle = build_bundle(data.model_copy(update={"body_weights": []}), now=NOW)
    assert "section" not in bundle["entry"][0]["resource"]  # no empty arrays in FHIR JSON
    assert check_bundle(bundle) == []


def test_check_flags_dangling_reference(data):
    bundle = build_bundle(data, now=NOW)
    bundle["entry"].pop()  # drop the last weight but keep the Composition reference
    assert any("unresolved reference" in p for p in check_bundle(bundle))


def test_check_flags_mixed_versions(data):
    bundle = build_bundle(data, now=NOW)
    meta = bundle["entry"][1]["resource"]["meta"]
    meta["profile"] = [meta["profile"][0].replace("|1.1.0", "|1.0.0")]
    assert any("version differs" in p for p in check_bundle(bundle))


def test_naive_timestamp_is_rejected():
    with pytest.raises(ValidationError):
        DigaExport.model_validate(
            {
                **json.loads(EXAMPLE.read_text(encoding="utf-8")),
                "body_weights": [{"measured_at": "2026-09-01T07:12:00", "kg": 90}],
            }
        )


def test_duplicate_measurement_is_rejected():
    raw = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    raw["body_weights"].append(raw["body_weights"][0])
    with pytest.raises(ValidationError, match="duplicate body_weights"):
        DigaExport.model_validate(raw)


def test_measurement_outside_period_is_rejected():
    raw = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    raw["body_weights"][0]["measured_at"] = "2026-10-01T07:00:00+02:00"
    with pytest.raises(ValidationError, match="outside period"):
        DigaExport.model_validate(raw)


def test_unknown_version_is_rejected(data):
    with pytest.raises(ValueError, match="not supported"):
        build_bundle(data, version="0.9.0")


def test_cli_build_then_check(tmp_path):
    out = tmp_path / "bundle.json"
    assert main(["build", str(EXAMPLE), "-o", str(out)]) == 0
    assert main(["check", str(out)]) == 0
