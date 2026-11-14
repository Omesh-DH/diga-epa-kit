"""Command line of diga-epa-kit: build, check, validate, explain-error, schema."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pydantic import ValidationError

from .bundle import build_bundle
from .explain import explain
from .input.model import DigaExport
from .terminology.versions import DEFAULT_VERSION, PACKS
from .validation import check_bundle
from .validator import ValidatorUnavailable, parse_report, validate


def _build(args: argparse.Namespace) -> int:
    try:
        data = DigaExport.model_validate_json(Path(args.input).read_text(encoding="utf-8"))
    except ValidationError as exc:
        print(f"invalid input: {exc}", file=sys.stderr)
        return 2
    bundle = build_bundle(data, version=args.mio_version)
    problems = check_bundle(bundle)
    out = json.dumps(bundle, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(out + "\n", encoding="utf-8")
    else:
        print(out)
    for p in problems:
        print(f"check: {p}", file=sys.stderr)
    return 1 if problems else 0


def _check(args: argparse.Namespace) -> int:
    bundle = json.loads(Path(args.bundle).read_text(encoding="utf-8"))
    problems = check_bundle(bundle)
    for p in problems:
        print(p)
    if not problems:
        print("ok")
    return 1 if problems else 0


def _schema(args: argparse.Namespace) -> int:
    out = json.dumps(DigaExport.model_json_schema(), ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(out + "\n", encoding="utf-8")
    else:
        print(out)
    return 0


def _validate(args: argparse.Namespace) -> int:
    # Exit codes as in scripts/validate.py: 1 errors, 3 validator unavailable, 4 inconclusive.
    try:
        report = validate(
            args.bundles,
            jar=Path(args.jar),
            packages=[Path(p) for p in args.ig],
            tx=args.tx,
            report_path=Path(args.report) if args.report else None,
        )
    except ValidatorUnavailable as exc:
        print(f"{exc}", file=sys.stderr)
        return 3
    for i in report.errors:
        print(f"ERROR {i.location}: {i.message}")
        if args.explain:
            print(f"      {explain(i.message).title}: {explain(i.message).text}")
    for i in report.timeouts:
        print(f"TIMEOUT {i.location}: {i.message}")
    print(f"{len(report.errors)} error(s), {len(report.warnings)} warning(s)")
    if not report.conclusive:
        print(f"{len(report.timeouts)} check(s) timed out: the run is inconclusive, rerun it")
        return 1 if report.errors else 4
    return 1 if report.errors else 0


def _explain(args: argparse.Namespace) -> int:
    if args.report:
        report = parse_report(json.loads(Path(args.report).read_text(encoding="utf-8")))
        messages = [f"{i.location}: {i.message}" for i in (*report.errors, *report.timeouts)]
        if not messages:
            print("the report contains no errors")
            return 0
    elif args.message:
        messages = [args.message]
    else:
        print("give a message or --report FILE", file=sys.stderr)
        return 2
    for m in messages:
        e = explain(m)
        print(m)
        print(f"  {e.title}")
        print(f"  {e.text}")
        if not e.about_bundle:
            print("  This finding says nothing about whether the bundle is correct.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="diga-epa-kit", description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", aliases=["convert"], help="turn a DiGA export JSON into a MIO DiGA Bundle")
    b.add_argument("input")
    b.add_argument("-o", "--output")
    b.add_argument("--mio-version", default=DEFAULT_VERSION, choices=sorted(PACKS))
    b.set_defaults(func=_build)

    c = sub.add_parser("check", help="run the fast local Bundle checks (no Java)")
    c.add_argument("bundle")
    c.set_defaults(func=_check)

    s = sub.add_parser("schema", help="print the JSON Schema of the input format")
    s.add_argument("-o", "--output")
    s.set_defaults(func=_schema)

    v = sub.add_parser("validate", help="run the HL7 FHIR validator on bundles (needs Java 17+)")
    v.add_argument("bundles", nargs="+")
    v.add_argument("--jar", required=True, help="path to validator_cli.jar")
    v.add_argument("--ig", action="append", default=[], help="profile package (.tgz); repeat per package")
    v.add_argument("--tx", default="n/a", help="terminology server URL, or n/a for none (default)")
    v.add_argument("--report", help="keep the validator's raw report at this path")
    v.add_argument("--explain", action="store_true", help="add a plain-language explanation to each error")
    v.set_defaults(func=_validate)

    e = sub.add_parser("explain-error", help="explain a validator message in plain language")
    e.add_argument("message", nargs="?")
    e.add_argument("--report", help="explain every error in a validator report file instead")
    e.set_defaults(func=_explain)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
