"""Licence gate for Python dependencies: every installed package must carry an allowed licence.

Usage: python scripts/check_licenses.py

Needs pip-licenses (in the dev extra). Runtime dependencies must be permissive;
copyleft that only touches unmodified dev tools (MPL-2.0) is allowed for those
tools by name. Spec files, the validator jar and terminology are not Python
packages and are covered by docs/licensing.md, not by this script.
"""

from __future__ import annotations

import json
import subprocess
import sys

# Matched as substrings of the licence string pip-licenses reports.
PERMISSIVE = ("MIT", "BSD", "Apache", "PSF", "Python Software Foundation", "ISC")
# Dev-only tools under weak copyleft, used unmodified and not shipped.
DEV_ONLY = {"pathspec": "Mozilla Public License 2.0"}


def main() -> int:
    out = subprocess.run(
        [sys.executable, "-m", "piplicenses", "--from=mixed", "--format=json"],
        capture_output=True,
        text=True,
    )
    if out.returncode != 0:
        print(f"pip-licenses failed: {out.stderr.strip() or out.stdout.strip()}", file=sys.stderr)
        return 2
    bad = []
    for pkg in json.loads(out.stdout):
        name, licence = pkg["Name"], pkg["License"]
        if any(p in licence for p in PERMISSIVE):
            continue
        if name in DEV_ONLY and DEV_ONLY[name] in licence:
            continue
        bad.append(f"{name} {pkg['Version']}: {licence}")
    for line in bad:
        print(f"NOT ALLOWED {line}")
    print(f"{len(bad)} package(s) with a licence outside the allowlist")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
