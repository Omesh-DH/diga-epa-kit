"""The verification gate: validate MIO DiGA bundles with the HL7 FHIR validator.

Usage: python scripts/validate.py [BUNDLE.json ...] [--tx URL] [--record]

Exit codes: 0 no errors, 1 errors, 2 setup problem, 3 validator crashed,
4 inconclusive (a check timed out, docs/gaps.md G10).

Without arguments it validates the golden bundles in tests/golden/. Profiles
come only from the pinned packages in spec/packages/ (run fetch_spec.py
first), never from the online registry.

With the default ``--tx n/a`` no terminology server is used: KBV CodeSystems
shipped in the packages are still checked, but SNOMED CT / LOINC codes and
displays are not. ``--tx https://tx.fhir.org/r4`` adds them (see docs/gaps.md
for the findings that mode always reports).

Validator 6.5.28 is pinned: newer releases abort on the snapshot-less KBV
package, older ones fail offline bindings (docs/decisions/0004-validator-pin.md).
"""

from __future__ import annotations

import argparse
import csv
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from _net import download
from fetch_spec import locked, tgz_path

from diga_epa_kit.validator import ValidatorUnavailable, validate

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / ".cache"
METRICS = ROOT / "research" / "metrics.csv"
VALIDATOR_VERSION = "6.5.28"
VALIDATOR_URL = "https://github.com/hapifhir/org.hl7.fhir.core/releases/download/{version}/validator_cli.jar"


def ensure_jar(version: str) -> Path:
    jar = CACHE / f"validator_cli-{version}.jar"
    if not jar.exists():
        download(VALIDATOR_URL.format(version=version), jar)
    return jar


def git_rev() -> str:
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True)
        return out.stdout.strip() or "uncommitted"
    except OSError:
        return "unknown"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("bundles", nargs="*")
    parser.add_argument("--tx", default="n/a")
    parser.add_argument("--report", default=str(CACHE / "validation-report.json"))
    parser.add_argument("--validator-version", default=VALIDATOR_VERSION)
    parser.add_argument("--record", action="store_true", help="append the result to research/metrics.csv")
    args = parser.parse_args()

    bundles = args.bundles or sorted(str(p) for p in (ROOT / "tests" / "golden").glob("*.json"))
    if not bundles:
        print("no bundles to validate", file=sys.stderr)
        return 2
    if not shutil.which("java"):
        print("java not found on PATH (need 17+)", file=sys.stderr)
        return 2
    packages = [tgz_path(p) for p in locked()]
    if missing := [p.name for p in packages if not p.exists()]:
        print(f"spec packages missing ({', '.join(missing)}); run scripts/fetch_spec.py", file=sys.stderr)
        return 2

    jar = ensure_jar(args.validator_version)
    # The validator's default tx cache is shared across runs, so an offline run
    # would silently reuse answers from an earlier online run. One cache per mode
    # and validator version.
    mode = "none" if args.tx == "n/a" else "online"
    tx_cache = CACHE / f"tx-{mode}-{args.validator_version}"
    tx_cache.mkdir(parents=True, exist_ok=True)
    try:
        result = validate(
            bundles, jar=jar, packages=packages, tx=args.tx, tx_cache=tx_cache, report_path=Path(args.report)
        )
    except ValidatorUnavailable as exc:
        print(f"{exc}", file=sys.stderr)
        return 3
    errors, warnings = result.errors, len(result.warnings)
    for i in errors:
        print(f"ERROR {i.location}: {i.message}")
    for i in result.timeouts:
        print(f"TIMEOUT {i.location}: {i.message}")
    print(f"{len(errors)} error(s), {warnings} warning(s); report: {args.report}")
    if not result.conclusive:
        # A timed-out check says nothing about the bundle (docs/gaps.md G10).
        print(f"{len(result.timeouts)} check(s) timed out: run is inconclusive, not recorded; rerun with nothing else running")
        return 1 if errors else 4

    if args.record:
        new = not METRICS.exists()
        METRICS.parent.mkdir(exist_ok=True)
        with METRICS.open("a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if new:
                w.writerow(["timestamp", "git_rev", "validator", "tx", "bundles", "errors", "warnings"])
            w.writerow([
                datetime.now(timezone.utc).isoformat(timespec="seconds"), git_rev(),
                args.validator_version, args.tx, len(bundles), len(errors), warnings,
            ])
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
