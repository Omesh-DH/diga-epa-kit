# Quickstart

From an empty folder to a validated MIO DiGA bundle. You need Python 3.10+
and, for the last step, Java 17+.

## 1. Install

```bash
python -m venv .venv
.venv/bin/pip install -e ".[dev]"      # Windows: .venv\Scripts\pip
python scripts/fetch_spec.py           # pinned KBV packages into spec/packages/
```

The profile packages and the validator are downloaded, not shipped: their
licences do not allow redistribution (docs/licensing.md).

## 2. Describe your data

The input is one JSON file per patient and export period. It needs no FHIR
knowledge. The smallest useful file:

```json
{
  "diga": {
    "name": "My App",
    "ve_id": "99990001",
    "version": "2.4.1",
    "pzn": "19999999",
    "manufacturer": {"name": "My Company GmbH"}
  },
  "patient": {"id": "5d2f8a44-1c3e-4b7a-8e55-6a9b0c1d2e3f", "birth_date": "1968-11-03", "gender": "male"},
  "period_start": "2026-09-01",
  "period_end": "2026-09-30",
  "body_weights": [{"measured_at": "2026-09-01T07:30:00+02:00", "kg": 101.4}]
}
```

- `patient.id` is your internal pseudonym. It is never exported; it only
  makes the resource ids stable.
- Every time needs a timezone offset.
- All fields and their limits: `diga-epa-kit schema`, or
  `docs/input-schema.json`. Complete examples for four kinds of app are in
  `synthetic/`. Use synthetic data only while testing.

## 3. Build and check

```bash
diga-epa-kit build my-export.json -o bundle.json
diga-epa-kit check bundle.json
```

`build` rejects implausible input (a weight of 0, a time outside the
period, a duplicate reading) with a message naming the field. `check` runs
fast structural checks without Java and prints `ok`.

## 4. Validate

```bash
diga-epa-kit validate bundle.json --jar .cache/validator_cli-6.5.28.jar \
  --ig spec/packages/kbv.mio.diga-1.1.0.tgz \
  --ig spec/packages/kbv.basis-1.3.0.tgz \
  --ig spec/packages/de.basisprofil.r4-1.3.2.tgz --explain
```

Inside this repository `python scripts/validate.py bundle.json` does the
same with the pinned versions and downloads the validator on first use.
Expect a few minutes: most of the time is the validator loading the
packages. The result is a line such as `0 error(s), 42 warning(s)`.

- **Errors** mean the bundle breaks a profile rule. `--explain` adds a
  plain-language explanation to each one;
  `diga-epa-kit explain-error "<message>"` does the same for one message.
- **Warnings** are expected. Without a terminology server the validator
  cannot check LOINC and SNOMED CT codes and says so for each of them.
- **TIMEOUT** means the validator gave up on a slow check; rerun with
  nothing else running.

## What the kit does not do

It produces the document. It does not send it to the ePA, and it covers
only part of the specification (docs/spec-inventory.md). Known problems in
the specification itself are listed in docs/gaps.md.
