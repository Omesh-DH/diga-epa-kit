"""The try-it page's build script and bridge module, tested in CPython (the page runs them in Pyodide)."""

import json
import subprocess
import sys
import zipfile

import pytest

from conftest import ROOT

sys.path.insert(0, str(ROOT / "site"))
import trykit  # noqa: E402


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    out = tmp_path_factory.mktemp("site")
    subprocess.run([sys.executable, str(ROOT / "scripts" / "build_site.py"), str(out)], check=True, capture_output=True)
    return out


def test_the_build_script_packs_the_kit_the_page_and_the_examples(site):
    for name in ("index.html", "app.js", "style.css", "diga_epa_kit.zip", "examples.json"):
        assert (site / name).is_file(), name
    names = zipfile.ZipFile(site / "diga_epa_kit.zip").namelist()
    assert "trykit.py" in names and "diga_epa_kit/__init__.py" in names
    assert "diga_epa_kit/epa_import/medication_list.py" in names
    assert not [n for n in names if "__pycache__" in n]


def test_every_example_on_the_page_builds_cleanly(site):
    examples = json.loads((site / "examples.json").read_text(encoding="utf-8"))
    assert len(examples["build"]) == len(list((ROOT / "synthetic").glob("archetype_*/*.json")))
    for example in examples["build"]:
        result = json.loads(trykit.build(json.dumps(example["data"])))
        assert result["stage"] == "done" and result["problems"] == [], example["label"]
    imported = json.loads(trykit.import_medication_list(json.dumps(examples["import"][0]["data"])))
    assert imported["stage"] == "done" and len(imported["medications"]) == 2


def test_build_reports_a_summary():
    data = json.loads((ROOT / "synthetic" / "archetype_a_mental" / "phq9_three_months.json").read_text("utf-8"))
    result = json.loads(trykit.build(json.dumps(data)))
    assert result["summary"]["resources"] == len(result["bundle"]["entry"])
    assert result["summary"]["profiles"]["Observation_Score_or_Assessment_by_Scale"] == 3
    assert result["summary"]["sections"] == [{"title": "Beurteilungen", "entries": 3}]


def test_bad_json_and_bad_input_are_explained():
    bad_json = json.loads(trykit.build('{"diga": '))
    assert bad_json["stage"] == "json" and bad_json["errors"][0]["where"].startswith("line 1")
    bad_input = json.loads(trykit.build(json.dumps({"diga": {}, "period_start": "2026-01-01"})))
    assert bad_input["stage"] == "input"
    wheres = {e["where"] for e in bad_input["errors"]}
    assert {"diga.name", "patient", "period_end"} <= wheres


def test_import_explains_what_it_cannot_read():
    assert json.loads(trykit.import_medication_list("[]"))["stage"] == "input"
    assert json.loads(trykit.import_medication_list("{"))["stage"] == "json"


def test_counted_kinds_name_only_known_fields_and_error_types():
    data = json.loads((ROOT / "synthetic" / "archetype_a_mental" / "phq9_three_months.json").read_text("utf-8"))
    data["Max Mustermann"] = "typed by a visitor"  # an unknown key must never be reported by name
    data["prom_scores"][0]["score"] = 99
    del data["patient"]
    result = json.loads(trykit.build(json.dumps(data)))
    assert result["kinds"] == ["(other):extra_forbidden", "patient:missing", "prom_scores:value_error"]
    assert "Mustermann" not in json.dumps(result["kinds"])
    assert json.loads(trykit.build("{"))["kinds"] == ["(json):invalid"]
    assert json.loads(trykit.import_medication_list("[]"))["kinds"] == ["(whole input):not_a_bundle"]


@pytest.mark.parametrize(
    "value,expected",
    [
        ("", None),
        ("https://diga-kit.goatcounter.com/count", "https://diga-kit.goatcounter.com/count"),
        ("http://localhost:8765/count", "http://localhost:8765/count"),
        ("https://evil.example.com/count", None),
        ("https://diga-kit.goatcounter.com/count?x=1", None),
    ],
)
def test_counting_is_off_unless_a_goatcounter_address_is_given(tmp_path, monkeypatch, value, expected):
    monkeypatch.setenv("DIGA_SITE_COUNTER", value)
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "build_site.py"), str(tmp_path)], check=True, capture_output=True
    )
    assert json.loads((tmp_path / "examples.json").read_text(encoding="utf-8"))["meta"]["counter"] == expected
