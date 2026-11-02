"""The verification gate: validate MIO DiGA bundles with the HL7 FHIR validator.

Usage: python scripts/validate.py [BUNDLE.json ...] [--tx URL] [--record]

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
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from _net import download
from fetch_spec import locked, tgz_path

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


def issues(outcome: dict) -> list[dict]:
    """Flatten the validator's -output: one OperationOutcome, or a Bundle of them."""
    if outcome.get("resourceType") == "Bundle":
        return [i for e in outcome.get("entry", []) for i in issues(e["resource"])]
    return outcome.get("issue", [])


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
    report = Path(args.report)
    report.parent.mkdir(parents=True, exist_ok=True)
    report.unlink(missing_ok=True)

    cmd = ["java", "-jar", str(jar), *bundles, "-version", "4.0.1"]
    for p in packages:
        cmd += ["-ig", str(p)]
    cmd += ["-tx", args.tx, "-txCache", str(tx_cache), "-output", str(report)]
    subprocess.run(cmd, check=False)

    if not report.exists():
        # The validator aborts without a report on internal failures, for
        # example when it cannot build a snapshot for a referenced profile.
        print("validator crashed before writing a report; see its output above", file=sys.stderr)
        return 3
    found = issues(json.loads(report.read_text(encoding="utf-8")))
    errors = [i for i in found if i.get("severity") in ("error", "fatal")]
    warnings = sum(1 for i in found if i.get("severity") == "warning")
    for i in errors:
        where = ", ".join(i.get("expression", [])) or "?"
        print(f"ERROR {where}: {i.get('details', {}).get('text') or i.get('diagnostics')}")
    print(f"{len(errors)} error(s), {warnings} warning(s); report: {report}")

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
