# Contributing

Thank you for helping. Bug reports, questions about the specification gaps and
pull requests are all welcome.

## Never post real patient data

Issues, pull requests, test data and examples must contain **synthetic data
only**. Describe a problem in words or attach a synthetic example. Anything
that looks like real patient data will be deleted.

## Set up

```bash
python -m venv .venv && .venv/bin/pip install -e ".[dev]"   # Windows: .venv\Scripts\pip
python scripts/fetch_spec.py     # pinned KBV, HL7 Deutschland and gematik packages
```

The validator needs Java 17 or newer.

## Before you open a pull request

```bash
ruff check . && ruff format --check . && mypy   # linting and types
python scripts/check_licenses.py                 # dependency licences
pytest -q                                        # unit and golden tests
python scripts/validate.py                       # HL7 validator, zero errors required
```

CI runs the same checks. The validator gate must report **zero errors**;
warnings are allowed.

## Rules for changes to the mapping

- `spec/packages/` is the only source of truth. Read the profile's
  StructureDefinition (and its base profiles) before mapping, including the
  `max: "0"` prohibitions.
- Never invent a code, display, system or version. Copy it from a package file
  and say in a comment where it came from.
- If the specification is unclear or contradicts itself, record it in
  `docs/gaps.md` instead of breaking a profile pattern to get a pass.
- A new mapper needs an input model, a mapping function, a reference bundle in
  `tests/golden/` and passing validator tests.
- No questionnaire item wording: export total scores and codes only, and add
  wording fragments of a new instrument to `docs/licensing/blocked-phrases.txt`.
- Keep commits small, with conventional messages (`feat(mapper): ...`).

## Reporting a problem with the try-it page

Use the "Report this problem on GitHub" link the page shows on every failure.
It fills in the error type and version without your input.
