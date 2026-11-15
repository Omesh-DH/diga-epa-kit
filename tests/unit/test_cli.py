import json
from pathlib import Path

import pytest

from diga_epa_kit import DigaExport
from diga_epa_kit.cli import main
from diga_epa_kit.explain import explain, is_known

ROOT = Path(__file__).parents[2]
EXAMPLE = ROOT / "synthetic" / "archetype_b_metabolic" / "weight_one_month.json"
SCHEMA = ROOT / "docs" / "input-schema.json"


def test_convert_is_an_alias_of_build(tmp_path):
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    assert main(["build", str(EXAMPLE), "-o", str(a)]) == 0
    assert main(["convert", str(EXAMPLE), "-o", str(b)]) == 0
    one, two = json.loads(a.read_text("utf-8")), json.loads(b.read_text("utf-8"))
    # Only the export time differs between two runs.
    assert [e["resource"]["id"] for e in one["entry"][1:]] == [e["resource"]["id"] for e in two["entry"][1:]]


def test_build_rejects_bad_input(tmp_path, capsys):
    bad = tmp_path / "bad.json"
    raw = json.loads(EXAMPLE.read_text("utf-8"))
    raw["body_weights"][0]["kg"] = -1
    bad.write_text(json.dumps(raw), encoding="utf-8")
    assert main(["build", str(bad)]) == 2
    assert "invalid input" in capsys.readouterr().err


def test_schema_command_prints_the_input_schema(capsys):
    assert main(["schema"]) == 0
    schema = json.loads(capsys.readouterr().out)
    assert schema == DigaExport.model_json_schema()
    assert {"diga", "patient", "period_start", "period_end"} <= set(schema["required"])


def test_committed_schema_is_current():
    # Regenerate with: diga-epa-kit schema -o docs/input-schema.json
    assert json.loads(SCHEMA.read_text("utf-8")) == DigaExport.model_json_schema()


# Messages as validator 6.5.28 printed them while this kit was built.
SEEN = [
    ("Observation.referenceRange.text: max allowed = 0, but found 1", "prohibited", True),
    ("Device.identifier: minimum required = 1, but only found 0", "Required element missing", True),
    (
        "Unable to find a profile match for urn:uuid:10767a42-7a08-53b2-92c9-95cea3a5a80d among choices: "
        "https://fhir.kbv.de/StructureDefinition/KBV_PR_MIO_DIGA_Observation_Score_or_Assessment_by_Scale|1.1.0",
        "Follow-on error",
        True,
    ),
    (
        "Slice 'Observation.method.coding:codeSnomed': a matching slice is required, but not found "
        "(from https://fhir.kbv.de/StructureDefinition/KBV_PR_MIO_DIGA_Observation_Glucose_Concentration|1.1.0)",
        "Required slice",
        True,
    ),
    (
        "The value provided ('LO') was not found in the value set 'QuantityComparator' "
        "(http://hl7.org/fhir/ValueSet/quantity-comparator|4.0.1), and a code is required from this value set",
        "required value set",
        True,
    ),
    ("None of the codings provided are in the value set 'IdentifierType'", "not in the bound value set", True),
    ("The value set 'doc-typecodes|4.0.1' validation (local) took too long to process (>60sec)", "timeout", False),
    (
        "A definition for CodeSystem 'http://loinc.org' version '2.72' could not be found, "
        "so the code cannot be validated. Valid versions: [3.1.0]",
        "not available offline",
        False,
    ),
    (
        "Unable to validate code 'kg' in system 'http://unitsofmeasure.org' because the validator "
        "is running without terminology services",
        "no terminology server",
        False,
    ),
    ("Constraint failed: dom-6: 'A resource should have narrative for robust management'", "narrative", False),
]


@pytest.mark.parametrize("message,title_part,about_bundle", SEEN, ids=[s[1] for s in SEEN])
def test_known_messages_are_explained(message, title_part, about_bundle):
    e = explain(message)
    assert is_known(message)
    assert title_part.lower() in e.title.lower()
    assert e.about_bundle is about_bundle


def test_unknown_message_gets_no_guess():
    e = explain("Something the kit has never seen")
    assert not is_known("Something the kit has never seen")
    assert e.title == "No explanation on file"
    assert "spec/packages" in e.text


def test_explain_error_command(capsys):
    assert main(["explain-error", "Device.identifier: minimum required = 1, but only found 0"]) == 0
    assert "Required element missing" in capsys.readouterr().out
    assert main(["explain-error"]) == 2


def test_explain_error_reads_a_report(tmp_path, capsys):
    report = tmp_path / "r.json"
    report.write_text(
        json.dumps(
            {
                "resourceType": "OperationOutcome",
                "issue": [
                    {
                        "severity": "error",
                        "code": "structure",
                        "expression": ["Bundle.entry[5].resource.referenceRange[0].text"],
                        "details": {"text": "Observation.referenceRange.text: max allowed = 0, but found 1"},
                    },
                    {"severity": "error", "code": "too-costly", "details": {"text": "took too long to process"}},
                    {"severity": "warning", "code": "informational", "details": {"text": "ignored"}},
                ],
            }
        ),
        encoding="utf-8",
    )
    assert main(["explain-error", "--report", str(report)]) == 0
    out = capsys.readouterr().out
    assert "Bundle.entry[5].resource.referenceRange[0].text" in out
    assert "Element prohibited by the profile" in out
    assert "says nothing about whether the bundle is correct" in out
    assert "ignored" not in out

    report.write_text(json.dumps({"resourceType": "OperationOutcome", "issue": []}), encoding="utf-8")
    assert main(["explain-error", "--report", str(report)]) == 0
    assert "no errors" in capsys.readouterr().out


def test_validate_command_reports_a_missing_java(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr("diga_epa_kit.validator.shutil.which", lambda _: None)
    assert main(["validate", str(EXAMPLE), "--jar", str(tmp_path / "v.jar")]) == 3
    assert "java" in capsys.readouterr().err
