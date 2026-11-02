"""Command line: ``diga-mio build`` and ``diga-mio check``."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pydantic import ValidationError

from .bundle import build_bundle
from .validation import check_bundle
from .input.model import DigaExport
from .terminology.versions import DEFAULT_VERSION, PACKS


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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="diga-epa-kit", description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="turn a DiGA export JSON into a MIO DiGA Bundle")
    b.add_argument("input")
    b.add_argument("-o", "--output")
    b.add_argument("--mio-version", default=DEFAULT_VERSION, choices=sorted(PACKS))
    b.set_defaults(func=_build)

    c = sub.add_parser("check", help="run the fast local Bundle checks")
    c.add_argument("bundle")
    c.set_defaults(func=_check)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
