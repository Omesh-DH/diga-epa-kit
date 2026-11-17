import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from conftest import package_resource
from diga_epa_kit import DigaExport, build_bundle, check_bundle

EXAMPLE = Path(__file__).parents[2] / "synthetic" / "archetype_b_metabolic" / "medication_from_epa.json"
NOW = datetime(2026, 11, 1, 9, 0, tzinfo=timezone.utc)
SD = "https://fhir.kbv.de/StructureDefinition/"
DRUG = f"{SD}KBV_PR_MIO_DIGA_Medication|1.1.0"
STATEMENT = f"{SD}KBV_PR_MIO_DIGA_MedicationStatement_Medication_Information|1.1.0"
SNOMED_VERSION = "http://snomed.info/sct/900000000000207008/version/20220331"


@pytest.fixture
def raw() -> dict:
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


@pytest.fixture
def bundle(raw) -> dict:
    return build_bundle(DigaExport.model_validate(raw), now=NOW)


def _build(raw):
    return build_bundle(DigaExport.model_validate(raw), now=NOW)


def _of(bundle, profile):
    return [e["resource"] for e in bundle["entry"] if e["resource"]["meta"]["profile"] == [profile]]


def _patient_ref(bundle):
    patient = next(e["resource"] for e in bundle["entry"] if e["resource"]["resourceType"] == "Patient")
    return {"reference": f"urn:uuid:{patient['id']}"}


def test_example_passes_local_checks(bundle):
    assert check_bundle(bundle) == []
    assert len(_of(bundle, DRUG)) == len(_of(bundle, STATEMENT)) == 2


def test_drug_with_a_pzn(bundle):
    drug = _of(bundle, DRUG)[0]
    assert drug["code"] == {
        "coding": [
            {
                "system": "http://fhir.de/CodeSystem/ifa/pzn",
                "version": "1.3.2",
                "code": "09999011",
                "display": "Synthetisches Präparat A 50 mg Filmtabletten",
            }
        ],
        "text": "Synthetisches Präparat A 50 mg Filmtabletten",
    }
    assert drug["identifier"][0]["value"] == f"urn:uuid:{drug['id']}"
    # Prohibited by the profile.
    assert not {"status", "manufacturer", "implicitRules", "language", "contained"} & set(drug)


def test_drug_without_a_pzn_is_named_in_text_only(bundle):
    assert _of(bundle, DRUG)[1]["code"] == {"text": "Synthetisches Vitaminpräparat B"}


def test_statement_shape(bundle):
    first, second = _of(bundle, STATEMENT)
    drugs = _of(bundle, DRUG)
    assert first["status"] == "unknown"
    assert first["medicationReference"] == {"reference": f"urn:uuid:{drugs[0]['id']}"}
    assert second["medicationReference"] == {"reference": f"urn:uuid:{drugs[1]['id']}"}
    assert first["subject"] == _patient_ref(bundle)
    assert first["effectivePeriod"] == {"start": "2026-09-14"}
    assert second["effectivePeriod"] == {"start": "2026-08-01", "end": "2026-10-10"}
    assert first["dateAsserted"] == "2026-09-14"
    assert first["dosage"] == [{"text": "1-0-1-0 Stück"}]
    assert "dosage" not in second
    assert first["note"] == [
        {"text": "Aus der ePA-Medikationsliste übernommen. Herkunft: Verschreibung. Status dort: offen."}
    ]
    assert first["identifier"][0]["value"] == f"urn:uuid:{first['id']}"
    prohibited = {
        "implicitRules", "language", "contained", "basedOn", "partOf", "category", "context", "derivedFrom",
        "reasonReference",
    }  # fmt: skip
    assert not prohibited & (set(first) | set(second))


def test_the_patient_is_named_as_the_information_source(bundle):
    # Required by the profile, which allows only persons; see docs/gaps.md G17.
    for statement in _of(bundle, STATEMENT):
        assert statement["informationSource"] == _patient_ref(bundle)


def test_statements_are_the_entries_of_the_medication_section(bundle):
    (section,) = bundle["entry"][0]["resource"]["section"]
    assert section["title"] == "Medikation"
    assert section["code"] == {
        "coding": [
            {
                "system": "http://snomed.info/sct",
                "version": SNOMED_VERSION,
                "code": "721912009",
                "display": "Medication summary document (record artifact)",
            }
        ]
    }
    assert [e["reference"] for e in section["entry"]] == [f"urn:uuid:{s['id']}" for s in _of(bundle, STATEMENT)]


def test_medication_section_sits_between_results_and_assessments(raw):
    raw["body_weights"] = [{"measured_at": "2026-10-05T07:00:00+02:00", "kg": 80.0}]
    raw["prom_scores"] = [{"instrument": "phq9", "completed_at": "2026-10-06T19:00:00+02:00", "score": 4}]
    titles = [s["title"] for s in _build(raw)["entry"][0]["resource"]["section"]]
    assert titles == ["Befunde und Ergebnisse", "Medikation", "Beurteilungen"]


@pytest.mark.parametrize("given,written", [("on_hold", "on-hold"), ("not_taken", "not-taken"), ("active", "active")])
def test_status_is_written_as_the_fhir_code(raw, given, written):
    raw["medications"][0]["status"] = given
    assert _of(_build(raw), STATEMENT)[0]["status"] == written


def test_ids_are_stable_and_do_not_leak_the_source_key(raw, bundle):
    again = _build(raw)
    assert [e["resource"]["id"] for e in bundle["entry"]] == [e["resource"]["id"] for e in again["entry"]]
    text = json.dumps(bundle)
    assert raw["medications"][0]["id"] not in text and raw["patient"]["id"] not in text


def test_no_dates_means_no_period(raw):
    for key in ("since", "until", "asserted_on"):
        raw["medications"][1].pop(key, None)
    statement = _of(_build(raw), STATEMENT)[1]
    assert "effectivePeriod" not in statement and "dateAsserted" not in statement


@pytest.mark.parametrize(
    "field,bad",
    [
        ("pzn", "1234567"),
        ("pzn", "123456789"),
        ("pzn", "1234567A"),
        ("status", "entered-in-error"),
        ("status", "on-hold"),
        ("name", ""),
        ("name", " padded "),
        ("name", "x" * 301),
        ("dosage_text", ""),
        ("note", ""),
        ("note", "x" * 501),
        ("id", "has space"),
    ],
)
def test_bad_values_are_rejected(raw, field, bad):
    raw["medications"][0][field] = bad
    with pytest.raises(ValidationError):
        DigaExport.model_validate(raw)


def test_status_and_name_are_required(raw):
    for field in ("status", "name", "id"):
        entry = dict(raw["medications"][0])
        del entry[field]
        with pytest.raises(ValidationError):
            DigaExport.model_validate({**raw, "medications": [entry]})


def test_date_rules(raw):
    raw["medications"][1]["until"] = "2026-07-31"
    with pytest.raises(ValidationError, match="until is before since"):
        DigaExport.model_validate(raw)
    raw["medications"][1]["until"] = "2026-10-10"
    raw["medications"][0]["since"] = "2026-11-01"
    with pytest.raises(ValidationError, match="after period_end"):
        DigaExport.model_validate(raw)


def test_a_medication_may_be_older_than_the_period(raw):
    raw["medications"][0]["since"] = "2019-03-01"
    assert DigaExport.model_validate(raw).medications[0].since.year == 2019


def test_duplicate_ids_are_rejected(raw):
    raw["medications"].append(dict(raw["medications"][0]))
    with pytest.raises(ValidationError, match="duplicate medications.id"):
        DigaExport.model_validate(raw)


# --- Against the pinned packages; skipped where they are not fetched.


def test_profile_rules_the_mapper_relies_on():
    drug = {
        e["id"]: e
        for e in package_resource("kbv.mio.diga#1.1.0", f"{SD}KBV_PR_MIO_DIGA_Medication")["differential"]["element"]
    }
    statement = {
        e["id"]: e
        for e in package_resource(
            "kbv.mio.diga#1.1.0", f"{SD}KBV_PR_MIO_DIGA_MedicationStatement_Medication_Information"
        )["differential"]["element"]
    }
    assert drug["Medication.status"]["max"] == "0"
    assert drug["Medication.code.coding:pznCode.version"]["min"] == 1
    assert drug["Medication.code.coding:pznCode.display"]["min"] == 1
    assert statement["MedicationStatement.informationSource"]["min"] == 1
    targets = statement["MedicationStatement.informationSource"]["type"][0]["targetProfile"]
    # Only persons can be the source: no device, no organisation, no service (docs/gaps.md G17).
    assert sorted(t.rsplit("_", 1)[-1].split("|")[0] for t in targets) == [
        "Patient",
        "Practitioner",
        "PractitionerRole",
        "RelatedPerson",
    ]


def test_pzn_version_is_the_one_the_code_system_definition_states(bundle):
    definition = package_resource("de.basisprofil.r4#1.3.2", "http://fhir.de/CodeSystem/ifa/pzn")
    assert _of(bundle, DRUG)[0]["code"]["coding"][0]["version"] == definition["version"] == "1.3.2"
