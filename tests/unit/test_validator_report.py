"""Reading the validator's report, without running Java."""

import pytest

from diga_epa_kit import validate
from diga_epa_kit.validator import ValidatorUnavailable, parse_report


def _outcome(*issues):
    return {"resourceType": "OperationOutcome", "issue": list(issues)}


ERROR = {
    "severity": "error",
    "code": "structure",
    "expression": ["Bundle.entry[1].resource.identifier"],
    "details": {"text": "Device.identifier: minimum required = 1, but only found 0"},
}
WARNING = {"severity": "warning", "code": "code-invalid", "diagnostics": "cannot be validated"}
TIMEOUT = {
    "severity": "error",
    "code": "too-costly",
    "expression": ["Bundle.entry[0].resource.type"],
    "details": {"text": "validation (local) took too long to process (>60sec)"},
}


def test_clean_report_is_ok():
    report = parse_report(_outcome(WARNING, {"severity": "information", "code": "informational"}))
    assert report.ok and report.conclusive
    assert (len(report.errors), len(report.warnings), len(report.timeouts)) == (0, 1, 0)
    # Without details.text the message falls back to diagnostics, and the location to "?".
    assert (report.warnings[0].message, report.warnings[0].location) == ("cannot be validated", "?")


def test_errors_are_reported_with_location_and_message():
    report = parse_report(_outcome(ERROR, {**ERROR, "severity": "fatal"}))
    assert not report.ok and report.conclusive
    assert len(report.errors) == 2
    assert report.errors[0].location == "Bundle.entry[1].resource.identifier"
    assert "minimum required = 1" in report.errors[0].message


def test_timeout_is_not_a_bundle_error_but_makes_the_run_inconclusive():
    # docs/gaps.md G10
    report = parse_report(_outcome(TIMEOUT, WARNING))
    assert report.errors == []
    assert len(report.timeouts) == 1
    assert not report.conclusive and not report.ok


def test_timeout_does_not_hide_a_real_error():
    report = parse_report(_outcome(TIMEOUT, ERROR))
    assert len(report.errors) == 1 and len(report.timeouts) == 1


def test_several_files_come_as_a_bundle_of_outcomes():
    report = parse_report(
        {"resourceType": "Bundle", "entry": [{"resource": _outcome(ERROR)}, {"resource": _outcome(WARNING, TIMEOUT)}]}
    )
    assert (len(report.errors), len(report.warnings), len(report.timeouts)) == (1, 1, 1)


def test_validate_needs_at_least_one_bundle(tmp_path):
    with pytest.raises(ValueError):
        validate([], jar=tmp_path / "v.jar", packages=[])


def test_missing_java_is_reported(monkeypatch, tmp_path):
    monkeypatch.setattr("diga_epa_kit.validator.shutil.which", lambda _: None)
    with pytest.raises(ValidatorUnavailable, match="java"):
        validate({"resourceType": "Bundle"}, jar=tmp_path / "v.jar", packages=[])
