"""Fetch the pinned FHIR packages into spec/packages/ and verify their hashes.

Each package lands twice: the .tgz the validator loads with -ig, and an
extracted folder <name>#<version>/ for reading the StructureDefinitions.

``packages`` in the lock are the ones the gate loads. ``reference_packages``
are pinned and fetched the same way but only read, for example the gematik
ePA medication model behind the import (docs/decisions/0009).
"""

from __future__ import annotations

import json
import sys
import tarfile
from pathlib import Path

from _net import download, sha256

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "spec"
PACKAGES = SPEC / "packages"


def locked() -> list[dict]:
    """The packages the validator gate loads."""
    return json.loads((SPEC / "packages.lock.json").read_text(encoding="utf-8"))["packages"]


def reference() -> list[dict]:
    """Pinned packages that are read but not loaded by the gate."""
    return json.loads((SPEC / "packages.lock.json").read_text(encoding="utf-8")).get("reference_packages", [])


def tgz_path(pkg: dict) -> Path:
    return PACKAGES / f"{pkg['name']}-{pkg['version']}.tgz"


def main() -> int:
    for pkg in [*locked(), *reference()]:
        tgz = tgz_path(pkg)
        if not tgz.exists() or sha256(tgz) != pkg["sha256"]:
            download(pkg["url"], tgz)
        actual = sha256(tgz)
        if actual != pkg["sha256"]:
            tgz.unlink()
            print(f"{pkg['name']}#{pkg['version']}: sha256 {actual} does not match lock", file=sys.stderr)
            return 1
        folder = PACKAGES / f"{pkg['name']}#{pkg['version']}"
        if not folder.exists():
            with tarfile.open(tgz) as tar:
                tar.extractall(folder, filter="data")
        print(f"ok {pkg['name']}#{pkg['version']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
