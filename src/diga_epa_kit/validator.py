"""Run the HL7 FHIR validator on bundles and read its result.

The library does not ship or download the validator jar or the profile
packages (third-party files, docs/licensing.md): the caller passes their
paths. In this repository ``scripts/validate.py`` does that with the pinned
versions. Needs Java 17+ on PATH.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

Json = dict[str, Any]

# The validator gives up on a slow check with this issue code. It says nothing
# about the bundle, so it must not count as a bundle error (docs/gaps.md G10).
TIMEOUT_CODE = "too-costly"


class ValidatorUnavailable(RuntimeError):
    """Java is missing, or the validator ended without writing a report."""


@dataclass(frozen=True)
class Issue:
    severity: str
    code: str
    location: str
    message: str


@dataclass(frozen=True)
class Report:
    issues: tuple[Issue, ...] = field(default_factory=tuple)

    @property
    def timeouts(self) -> list[Issue]:
        return [i for i in self.issues if i.code == TIMEOUT_CODE and i.severity in ("error", "fatal")]

    @property
    def errors(self) -> list[Issue]:
        return [i for i in self.issues if i.severity in ("error", "fatal") and i.code != TIMEOUT_CODE]

    @property
    def warnings(self) -> list[Issue]:
        return [i for i in self.issues if i.severity == "warning"]

    @property
    def conclusive(self) -> bool:
        """False when a check timed out: the run must be repeated before it means anything."""
        return not self.timeouts

    @property
    def ok(self) -> bool:
        return self.conclusive and not self.errors


def parse_report(outcome: Json) -> Report:
    """Read the validator's ``-output`` file: one OperationOutcome, or a Bundle of them."""
    return Report(tuple(_issues(outcome)))


def _issues(outcome: Json) -> list[Issue]:
    if outcome.get("resourceType") == "Bundle":
        return [i for e in outcome.get("entry", []) for i in _issues(e["resource"])]
    return [
        Issue(
            severity=i.get("severity", ""),
            code=i.get("code", ""),
            location=", ".join(i.get("expression", [])) or "?",
            message=(i.get("details") or {}).get("text") or i.get("diagnostics") or "",
        )
        for i in outcome.get("issue", [])
    ]


def validate(
    bundles: Json | Path | str | Sequence[Json | Path | str],
    *,
    jar: Path,
    packages: Sequence[Path],
    tx: str = "n/a",
    tx_cache: Path | None = None,
    report_path: Path | None = None,
) -> Report:
    """Validate one or more bundles (dicts or file paths) against the given packages."""
    if isinstance(bundles, (dict, str, Path)):
        bundles = [bundles]
    if not bundles:
        raise ValueError("no bundles to validate")
    if not shutil.which("java"):
        raise ValidatorUnavailable("java not found on PATH (need 17+)")

    with tempfile.TemporaryDirectory() as tmp:
        paths: list[str] = []
        for n, b in enumerate(bundles):
            if isinstance(b, dict):
                p = Path(tmp) / f"bundle-{n}.json"
                p.write_text(json.dumps(b), encoding="utf-8")
                paths.append(str(p))
            else:
                paths.append(str(b))
        report = Path(report_path) if report_path else Path(tmp) / "report.json"
        report.parent.mkdir(parents=True, exist_ok=True)
        report.unlink(missing_ok=True)

        cmd = ["java", "-jar", str(jar), *paths, "-version", "4.0.1"]
        for pkg in packages:
            cmd += ["-ig", str(pkg)]
        cmd += ["-tx", tx]
        if tx_cache:
            cmd += ["-txCache", str(tx_cache)]
        cmd += ["-output", str(report)]
        subprocess.run(cmd, check=False)

        if not report.exists():
            # The validator aborts without a report on internal failures, for
            # example when it cannot build a snapshot for a referenced profile.
            raise ValidatorUnavailable("validator ended without writing a report; see its output")
        return parse_report(json.loads(report.read_text(encoding="utf-8")))
