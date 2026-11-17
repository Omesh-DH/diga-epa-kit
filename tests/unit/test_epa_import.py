"""Reading an ePA medication list (gematik eML) into the input model."""

import json

import pytest

from conftest import ROOT
from diga_epa_kit import DigaExport
from diga_epa_kit.cli import main
from diga_epa_kit.epa_import import read_medication_list

EML = ROOT / "synthetic" / "epa_import" / "medication_list.json"
EXPORT = ROOT / "synthetic" / "archetype_b_metabolic" / "medication_from_epa.json"
PREFIX = "MedicationStatement/7c0f2a1e-0000-4000-8000-0000000000"


@pytest.fixture
def eml() -> dict:
    return json.loads(EML.read_text(encoding="utf-8"))


def _dump(result):
    return [m.model_dump(mode="json", exclude_none=True) for m in result.medications]


def test_the_export_example_is_exactly_what_the_reader_produces(eml):
    expected = json.loads(EXPORT.read_text(encoding="utf-8"))["medications"]
    assert _dump(read_medication_list(eml)) == expected
    # And the whole round trip validates as kit input.
    DigaExport.model_validate(json.loads(EXPORT.read_text(encoding="utf-8")))


def test_what_is_read(eml):
    first, second = read_medication_list(eml).medications
    assert (first.name, first.pzn) == ("Synthetisches Präparat A 50 mg Filmtabletten", "09999011")
    assert first.dosage_text == "1-0-1-0 Stück"
    assert (first.since.isoformat(), first.until, first.asserted_on.isoformat()) == ("2026-09-14", None, "2026-09-14")
    # A manual entry without a PZN, referenced by an absolute URL, with a dateTime as start.
    assert (second.name, second.pzn, second.dosage_text) == ("Synthetisches Vitaminpräparat B", None, None)
    assert (second.since.isoformat(), second.until.isoformat()) == ("2026-08-01", "2026-10-10")
    assert first.status == second.status == "unknown"


def test_what_is_skipped_and_why(eml):
    skipped = {f.reference: f.reason for f in read_medication_list(eml).skipped}
    assert skipped == {
        f"{PREFIX}13": "entered in error",
        f"{PREFIX}14": "the medication has no name",
        f"{PREFIX}15": "the medication it refers to is not in the bundle",
    }


def test_no_personal_data_of_anyone_is_read(eml):
    # The bundle also holds the insurance number, the patient's name, the prescriber and the pharmacy.
    text = json.dumps(_dump(read_medication_list(eml)), ensure_ascii=False)
    for secret in (
        "A000000000", 'Synthetisch"', "Verordnerin", "Apotheke", "1-1.00.00000000", "3-0.00.00000000", "1964-02-27",
    ):  # fmt: skip
        assert secret not in text, secret


def test_reader_survives_damaged_entries(eml):
    statements = [e["resource"] for e in eml["entry"] if e["resource"]["resourceType"] == "MedicationStatement"]
    statements[0]["status"] = "draft"  # not a MedicationStatement status
    del statements[1]["medicationReference"]
    eml["entry"].append({"resource": {"resourceType": "MedicationStatement"}})
    eml["entry"].append({})
    result = read_medication_list(eml)
    assert result.medications == []
    reasons = [f.reason for f in result.skipped]
    assert "status 'draft' is not supported" in reasons
    assert "status None is not supported" in reasons
    assert len(result.skipped) == 6


def test_a_malformed_pzn_is_dropped_with_a_note(eml):
    drug = next(e["resource"] for e in eml["entry"] if e["resource"]["resourceType"] == "Medication")
    drug["code"]["coding"][0]["code"] = "9999011"
    result = read_medication_list(eml)
    assert result.medications[0].pzn is None and result.medications[0].name.startswith("Synthetisches Präparat A")
    assert [f.reason for f in result.notes] == ["PZN is not 8 digits; imported by name only"]


def test_a_partial_start_date_is_left_out_with_a_note(eml):
    statement = next(e["resource"] for e in eml["entry"] if e["resource"]["resourceType"] == "MedicationStatement")
    statement["effectivePeriod"] = {"start": "2026-09"}
    result = read_medication_list(eml)
    assert result.medications[0].since is None
    assert [f.reason for f in result.notes] == ["start is not a full date; left out"]


def test_an_overlong_name_is_skipped_not_truncated(eml):
    drug = next(e["resource"] for e in eml["entry"] if e["resource"]["resourceType"] == "Medication")
    drug["code"]["text"] = "x" * 301
    result = read_medication_list(eml)
    assert len(result.medications) == 1
    assert any(f.reason.startswith("name:") for f in result.skipped)


@pytest.mark.parametrize("bad", [{}, {"resourceType": "Patient"}, [], "text", None])
def test_only_a_bundle_is_accepted(bad):
    with pytest.raises(ValueError, match="not a FHIR Bundle"):
        read_medication_list(bad)


def test_an_empty_bundle_gives_nothing():
    result = read_medication_list({"resourceType": "Bundle", "type": "searchset"})
    assert (result.medications, result.skipped, result.notes) == ([], [], [])


def test_cli_import_medication(tmp_path, capsys):
    out = tmp_path / "medications.json"
    assert main(["import-medication", str(EML), "-o", str(out)]) == 0
    fragment = json.loads(out.read_text(encoding="utf-8"))
    assert fragment == {"medications": json.loads(EXPORT.read_text(encoding="utf-8"))["medications"]}
    err = capsys.readouterr().err
    assert "2 imported, 3 skipped" in err and "entered in error" in err

    not_a_bundle = tmp_path / "x.json"
    not_a_bundle.write_text("{}", encoding="utf-8")
    assert main(["import-medication", str(not_a_bundle)]) == 2


def test_reader_handles_the_example_in_the_gematik_package():
    # gematik's own example list; read from the pinned package, never copied into the repo.
    path = ROOT / "spec" / "packages" / "de.gematik.epa.medication#1.3.5" / "package" / "example"
    path = path / "Bundle-example-get-medication-list-bundle1.json"
    if not path.exists():
        pytest.skip("pinned package de.gematik.epa.medication#1.3.5 not fetched (scripts/fetch_spec.py)")
    bundle = json.loads(path.read_text(encoding="utf-8"))
    result = read_medication_list(bundle)
    assert [m.pzn for m in result.medications] == ["00814665", "11722423", "06313728"]
    assert result.skipped == []
    # gematik's example is the first page of 16 entries.
    assert [f.reason for f in result.notes] == ["the bundle is one page of a longer list; read the other pages too"]
    # The example patient's insurance number and name stay behind.
    text = json.dumps(_dump(result), ensure_ascii=False)
    patient = next(e["resource"] for e in bundle["entry"] if e["resource"]["resourceType"] == "Patient")
    assert patient["identifier"][0]["value"] not in text and patient["name"][0]["family"] not in text


def test_the_note_says_where_an_entry_came_from_in_gematiks_words(eml):
    first, second = read_medication_list(eml).medications
    assert first.note == "Aus der ePA-Medikationsliste übernommen. Herkunft: Verschreibung. Status dort: offen."
    assert second.note == "Aus der ePA-Medikationsliste übernommen. Herkunft: Nachtrag. Status dort: offen."


def test_status_and_origin_labels_come_from_the_gematik_package():
    package = ROOT / "spec" / "packages" / "de.gematik.epa.medication#1.3.5" / "package"
    if not package.exists():
        pytest.skip("pinned package de.gematik.epa.medication#1.3.5 not fetched (scripts/fetch_spec.py)")
    from diga_epa_kit.epa_import import medication_list as reader

    status_vs = json.loads((package / "ValueSet-epa-medication-statement-status-vs.json").read_text("utf-8"))
    labels = {
        c["code"]: c["designation"][0]["value"] for inc in status_vs["compose"]["include"] for c in inc["concept"]
    }
    assert all(labels[code] == german for code, german in reader._STATUS_DE.items())
    assert set(labels) == reader._EML_STATUS
    contexts = json.loads((package / "CodeSystem-context-code.json").read_text("utf-8"))["concept"]
    assert {c["code"]: c["designation"][0]["value"] for c in contexts} == reader._CONTEXT_DE


def test_paging_is_reported(eml):
    eml["link"] = [{"relation": "next", "url": "https://example.org/next"}]
    assert "one page of a longer list" in read_medication_list(eml).notes[0].reason


def test_a_point_in_time_is_not_turned_into_a_start(eml):
    statement = next(e["resource"] for e in eml["entry"] if e["resource"]["resourceType"] == "MedicationStatement")
    del statement["effectivePeriod"]
    statement["effectiveDateTime"] = "2026-09-14"
    result = read_medication_list(eml)
    assert result.medications[0].since is None
    assert "effectiveDateTime is a point in time, not a period; left out" in [f.reason for f in result.notes]


@pytest.mark.parametrize("field", ["end", "dateAsserted"])
def test_a_bad_end_or_assertion_date_is_reported(eml, field):
    statement = [e["resource"] for e in eml["entry"] if e["resource"]["resourceType"] == "MedicationStatement"][1]
    if field == "end":
        statement["effectivePeriod"]["end"] = "2026-10"
    else:
        statement["dateAsserted"] = "2026-08"
    result = read_medication_list(eml)
    assert f"{field} is not a full date; left out" in [f.reason for f in result.notes]


def test_a_versioned_reference_is_resolved(eml):
    statement = next(e["resource"] for e in eml["entry"] if e["resource"]["resourceType"] == "MedicationStatement")
    statement["medicationReference"]["reference"] += "/_history/2"
    assert read_medication_list(eml).medications[0].pzn == "09999011"


def test_an_overlong_dosage_drops_the_dosage_not_the_entry(eml):
    statement = next(e["resource"] for e in eml["entry"] if e["resource"]["resourceType"] == "MedicationStatement")
    statement["extension"][1]["valueMarkdown"] = "x" * 1001
    result = read_medication_list(eml)
    assert result.medications[0].dosage_text is None and result.medications[0].pzn == "09999011"
    assert "dosage text longer than 1000 characters; left out" in [f.reason for f in result.notes]


def test_a_status_outside_the_eml_value_set_is_noted(eml):
    statement = next(e["resource"] for e in eml["entry"] if e["resource"]["resourceType"] == "MedicationStatement")
    statement["status"] = "active"
    result = read_medication_list(eml)
    assert result.medications[0].status == "active"
    assert "status 'active' is not an eML status; imported as given" in [f.reason for f in result.notes]


def test_cli_reports_a_missing_file(tmp_path, capsys):
    assert main(["import-medication", str(tmp_path / "missing.json")]) == 2
    assert "cannot read" in capsys.readouterr().err
