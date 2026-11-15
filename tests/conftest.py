import json
from datetime import datetime, timezone
from functools import cache
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SYNTHETIC = sorted((ROOT / "synthetic").glob("archetype_*/*.json"))

# Golden files and the validator suite build with this clock so output is stable.
FIXED_NOW = datetime(2026, 11, 1, 9, 0, tzinfo=timezone.utc)


def synthetic_id(path: Path) -> str:
    return f"{path.parent.name}__{path.stem}"


@cache
def _package_index(package: str) -> dict[str, Path]:
    index: dict[str, Path] = {}
    for path in sorted((ROOT / "spec" / "packages" / package / "package").glob("*.json")):
        try:
            res = json.loads(path.read_text(encoding="utf-8"))
        except ValueError:
            continue
        if isinstance(res, dict) and isinstance(res.get("url"), str):
            index[res["url"]] = path
    return index


def package_resource(package: str, url: str) -> dict:
    """A resource from a pinned package, found by its canonical URL.

    File names are no use for this: their case differs from the URL, which only works on a
    case-insensitive file system. The packages are fetched, not committed, so without the
    package the test is skipped; with it, a missing resource is a failure.
    """
    if not (ROOT / "spec" / "packages" / package / "package").is_dir():
        pytest.skip(f"pinned package {package} not fetched (scripts/fetch_spec.py)")
    index = _package_index(package)
    assert url in index, f"{url} not found in {package}"
    return json.loads(index[url].read_text(encoding="utf-8"))
