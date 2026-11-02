"""Every synthetic input must build to exactly its reviewed golden bundle.

A diff here means a mapper changed output. If the change is intended, run
``UPDATE_GOLDEN=1 pytest tests/golden`` and review the JSON diff before
committing it.
"""

import json
import os

import pytest
from conftest import FIXED_NOW, SYNTHETIC, ROOT, synthetic_id

from diga_epa_kit import DigaExport, build_bundle

GOLDEN = ROOT / "tests" / "golden"


@pytest.mark.parametrize("src", SYNTHETIC, ids=synthetic_id)
def test_matches_golden(src):
    bundle = build_bundle(DigaExport.model_validate_json(src.read_text(encoding="utf-8")), now=FIXED_NOW)
    golden = GOLDEN / f"{synthetic_id(src)}.json"
    if os.environ.get("UPDATE_GOLDEN"):
        golden.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    assert golden.exists(), f"no golden file; run UPDATE_GOLDEN=1 pytest {__file__}"
    assert bundle == json.loads(golden.read_text(encoding="utf-8"))
