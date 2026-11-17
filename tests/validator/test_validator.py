"""The gate as a test. Deselected by default (pyproject addopts); run with ``pytest -m validator``."""

import json
import shutil
import subprocess
import sys

import pytest

from conftest import ROOT

pytestmark = [
    pytest.mark.validator,
    pytest.mark.skipif(not shutil.which("java"), reason="java not on PATH"),
]
GOLDEN = sorted((ROOT / "tests" / "golden").glob("*.json"))


def _validate(paths, tmp_path):
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "validate.py"), *map(str, paths), "--report", str(tmp_path / "r.json")],
        capture_output=True,
        text=True,
    )
    return proc, [line for line in proc.stdout.splitlines() if line.startswith("ERROR")]


def test_golden_bundles_have_no_validator_errors(tmp_path):
    assert GOLDEN, "no golden bundles"
    proc, errors = _validate(GOLDEN, tmp_path)
    assert proc.returncode == 0, "\n".join(errors) or proc.stderr[-2000:]


def test_negative_control_is_rejected(tmp_path):
    """Known violations must surface, or the gate is checking nothing."""
    bundle = json.loads((ROOT / "tests" / "golden" / "archetype_a_mental__phq9_three_months.json").read_text("utf-8"))
    score = next(e["resource"] for e in bundle["entry"] if e["resource"]["resourceType"] == "Observation")
    score["referenceRange"][0]["text"] = "prohibited by profile"
    device = next(e["resource"] for e in bundle["entry"] if e["resource"]["resourceType"] == "Device")
    del device["identifier"]
    bad = tmp_path / "negative.json"
    bad.write_text(json.dumps(bundle), encoding="utf-8")

    # The glucose method coding with the SNOMED version its value set states instead of the
    # one the profile pattern fixes (docs/gaps.md G15).
    glucose = json.loads((ROOT / "tests" / "golden" / "archetype_b_metabolic__glucose_diary.json").read_text("utf-8"))
    reading = next(e["resource"] for e in glucose["entry"] if "method" in e["resource"])
    reading["method"]["coding"][0]["version"] = "http://snomed.info/sct/900000000000207008/version/20220131"
    bad_version = tmp_path / "negative_method_version.json"
    bad_version.write_text(json.dumps(glucose), encoding="utf-8")

    # A comparator code FHIR does not define. If the gate did not check the code, its accepting
    # "<" and ">" on out-of-range glucose readings would mean nothing (docs/gaps.md G16).
    sensor = json.loads(
        (ROOT / "tests" / "golden" / "archetype_b_metabolic__glucose_sensor_out_of_range.json").read_text("utf-8")
    )
    marked = next(e["resource"] for e in sensor["entry"] if "comparator" in e["resource"].get("valueQuantity", {}))
    marked["valueQuantity"]["comparator"] = "LO"
    bad_comparator = tmp_path / "negative_comparator.json"
    bad_comparator.write_text(json.dumps(sensor), encoding="utf-8")

    # A comparator where the profile prohibits it: the contrast case of docs/gaps.md G16.
    vitals = json.loads((ROOT / "tests" / "golden" / "archetype_b_metabolic__home_vital_signs.json").read_text("utf-8"))
    heart_rate = next(e["resource"] for e in vitals["entry"] if "Heart_Rate" in e["resource"]["meta"]["profile"][0])
    heart_rate["valueQuantity"]["comparator"] = "<"
    bad_heart_rate = tmp_path / "negative_heart_rate_comparator.json"
    bad_heart_rate.write_text(json.dumps(vitals), encoding="utf-8")

    # A PZN coding without its required version, and a Medication.status the profile prohibits
    # (docs/gaps.md G18).
    meds = json.loads(
        (ROOT / "tests" / "golden" / "archetype_b_metabolic__medication_from_epa.json").read_text("utf-8")
    )
    drug = next(e["resource"] for e in meds["entry"] if e["resource"]["resourceType"] == "Medication")
    del drug["code"]["coding"][0]["version"]
    drug["status"] = "active"
    bad_medication = tmp_path / "negative_medication.json"
    bad_medication.write_text(json.dumps(meds), encoding="utf-8")

    proc, errors = _validate([bad, bad_version, bad_comparator, bad_heart_rate, bad_medication], tmp_path)
    assert proc.returncode == 1, proc.stderr[-2000:]
    assert any("referenceRange.text: max allowed = 0" in e for e in errors)
    assert any("Device.identifier: minimum required = 1" in e for e in errors)
    assert any("'Observation.method.coding:codeSnomed': a matching slice is required" in e for e in errors)
    assert any("was not found in the value set 'QuantityComparator'" in e for e in errors)
    assert any("valueQuantity.comparator: max allowed = 0" in e for e in errors)
    assert any("Medication.status: max allowed = 0" in e for e in errors)
    assert any("pznCode" in e and "version" in e for e in errors)


def test_library_validate_accepts_a_dict():
    """The same gate through ``diga_epa_kit.validate``, with a bundle held in memory."""
    sys.path.insert(0, str(ROOT / "scripts"))
    from diga_epa_kit import validate
    from fetch_spec import locked, tgz_path
    from validate import VALIDATOR_VERSION, ensure_jar

    bundle = json.loads((ROOT / "tests" / "golden" / "archetype_a_mental__phq9_three_months.json").read_text("utf-8"))
    report = validate(bundle, jar=ensure_jar(VALIDATOR_VERSION), packages=[tgz_path(p) for p in locked()])
    assert report.ok, report.errors or report.timeouts
    assert report.warnings
