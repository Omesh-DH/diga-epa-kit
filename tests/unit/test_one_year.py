"""One synthetic patient, one year of data: the kit must stay correct and fast at that size."""

import sys
import time

from conftest import ROOT

from diga_epa_kit import DigaExport, build_bundle, check_bundle

sys.path.insert(0, str(ROOT / "scripts"))
from bench_one_year import NOW, one_year_input  # noqa: E402


def test_one_year_builds_cleanly_and_quickly():
    raw = one_year_input()
    t0 = time.perf_counter()
    bundle = build_bundle(DigaExport.model_validate(raw), now=NOW)
    problems = check_bundle(bundle)
    elapsed = time.perf_counter() - t0

    assert problems == []
    # 365 each of weight, blood pressure, heart rate and steps, plus the rest.
    assert len(bundle["entry"]) == 1731
    urls = [e["fullUrl"] for e in bundle["entry"]]
    assert len(set(urls)) == len(urls)
    listed = sum(
        len(s.get("entry", [])) + sum(len(x["entry"]) for x in s.get("section", []))
        for s in bundle["entry"][0]["resource"]["section"]
    )
    # Everything except Composition, Patient, Device, DeviceDefinition and Organization is listed once.
    assert listed == len(bundle["entry"]) - 5
    # Measured at about 0.15 s; the bound only catches a change that makes it scale badly.
    assert elapsed < 10


def test_generator_is_deterministic():
    assert one_year_input() == one_year_input()
