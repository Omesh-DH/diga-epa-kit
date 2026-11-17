# diga-epa-kit

[![ci](https://github.com/Omesh-DH/diga-epa-kit/actions/workflows/ci.yml/badge.svg)](https://github.com/Omesh-DH/diga-epa-kit/actions/workflows/ci.yml)
[![licence: Apache-2.0](https://img.shields.io/badge/licence-Apache--2.0-blue.svg)](LICENSE)

Open-source Python kit that turns the data a German digital health app (DiGA)
typically holds into **KBV MIO DiGA 1.1.0** FHIR R4 document bundles for the
electronic patient record (ePA), and reads medication from the ePA's
medication list.

**Try it in your browser: https://omesh-dh.github.io/diga-epa-kit/**. The kit
runs inside the page, so your data never leaves your computer.

> **Not for production use.** This is not a certified medical device, it has
> not been tested against a real ePA, and it comes without warranty (see
> LICENSE). Use synthetic or test data only.

## What it does

- **Builds bundles.** Plain JSON in a simple input format (no FHIR knowledge
  needed) becomes one MIO DiGA document Bundle with deterministic ids.
- **Checks them.** Input is validated field by field before anything is
  exported; fast structural checks run in-process; `diga-epa-kit validate`
  runs the official HL7 FHIR validator against the pinned KBV packages.
- **Explains validator errors** in plain language (`diga-epa-kit explain-error`).
- **Reads the ePA medication list** (gematik `de.gematik.epa.medication` 1.3.5)
  into the same input format, reading only the medication entries and never
  the patient, prescriber or pharmacy data in the same list.
- **Documents the specification's own problems.** `docs/gaps.md` lists 19
  places where the MIO DiGA specification is unclear, contradicts itself or
  leaves a decision to the manufacturer, each tied to an element of the
  published profiles and, where possible, confirmed by the validator.

### Coverage

21 of the 44 MIO DiGA 1.1.0 profiles are mapped (`docs/spec-inventory.md`).
Every bundle carries Patient, Device_DIGA (VE-ID and PZN),
DeviceDefinition_DIGA and Organization_Manufacturer, plus:

| Area | Data | Profiles |
| --- | --- | --- |
| Questionnaires | PHQ-9, GAD-7, 0–10 pain rating, Oswestry Disability Index (total scores only, no item wording) | Observation_Score_or_Assessment_by_Scale |
| Vital signs | Body weight, body height, blood pressure, heart rate, temperature, oxygen saturation (pulse oximeter), respiratory rate, glucose (incl. sensor readings and LO/HI) | the nine Observation vital-sign profiles except head circumference |
| Other results | BMI, daily steps | Observation_Free |
| Patient reports | Diary entries | Observation_Diary_Entry |
| Goals and plans | Goals, care plans with activities | Goal, CarePlan |
| Medication | Medication, also read from an ePA medication list | Medication, MedicationStatement_Medication_Information |

Not covered yet, among others: Questionnaire and QuestionnaireResponse,
Provenance, attachments, and five profiles whose code systems cannot be
checked offline (decision `docs/decisions/0008-strict-offline-gate.md`).

## Quick start

```bash
python -m venv .venv && .venv/bin/pip install -e ".[dev]"   # Windows: .venv\Scripts\pip
python scripts/fetch_spec.py          # pinned FHIR packages into spec/packages/
diga-epa-kit build synthetic/archetype_a_mental/phq9_three_months.json -o out/phq9.json
diga-epa-kit check out/phq9.json      # fast in-process checks
python scripts/validate.py out/phq9.json   # HL7 FHIR validator, needs Java 17+
```

More commands:

```bash
diga-epa-kit schema                    # the input format as JSON Schema
diga-epa-kit explain-error "Device.identifier: minimum required = 1, but only found 0"
diga-epa-kit import-medication synthetic/epa_import/medication_list.json
```

Step by step: `docs/quickstart.md`. Functions, commands and which input field
becomes which resource: `docs/api.md`. Why each field is mapped the way it is:
`docs/mapping.md`. Synthetic example inputs for four kinds of app are in
`synthetic/`.

## How it is verified

- **The pinned specification is the only source of truth.** Every code,
  display and version is copied from the KBV, HL7 Deutschland or gematik
  package files pinned in `spec/packages.lock.json`, and the source is named.
- **Zero-error gate.** Every reference bundle in `tests/golden/` must pass the
  HL7 FHIR validator 6.5.28 offline with zero errors, locally and in CI.
  Currently 11 bundles, 0 errors.
- **Negative control.** The validator test plants known violations and checks
  that the validator rejects each of them, so a passing gate means something.
- **Tests and linting.** About 400 unit and golden tests, ruff and strict mypy,
  and a licence check of the Python dependencies, on Python 3.10 and 3.12.
- **Decisions are written down** in `docs/decisions/`.

Limits: the offline validator cannot check LOINC and SNOMED CT codes against
their terminologies (it warns instead), all data is synthetic, and nothing has
been tested against a real ePA or by KBV.

## The try-it page

`site/` runs the unchanged kit in the browser through Pyodide: pick a
synthetic example or paste your own input, build a bundle, see the local
checks and download it, or read an ePA medication list. The official HL7
validator does not run there. Locally: `python scripts/build_site.py`, then
`python -m http.server 8765 --directory site` and open http://localhost:8765.
`.github/workflows/pages.yml` publishes it on every push to `main`.

**Usage counting.** To learn whether the page works for people, it can count
anonymous events: page opened, kit loaded or failed to load, and whether each
build or import worked or failed, with the top-level field names and error
types of failures (for example `build-rejected:patient:missing`). It never
sends the input, values, names or the bundle, sets no cookies, and stops when
the visitor switches it off or the browser sends Do Not Track or Global
Privacy Control. Counting is off until the repository variable
`GOATCOUNTER_URL` holds a GoatCounter count address
(`https://CODE.goatcounter.com/count`). Every failure also offers a
pre-filled GitHub issue without the input.

## How it was built

The code was written with an AI coding assistant (Claude Code) under the
maintainer's direction, inside a strict loop: read the pinned profile, map,
generate the reference bundle, pass the zero-error validator gate, then an
independent review agent checks the change against the specification before
anything is committed. Decisions on open questions in the specification were
made by the maintainer and recorded. `CLAUDE.md` and `.claude/` contain the
working rules, commands and review agents.

## Contributing

Issues and pull requests are welcome; see `CONTRIBUTING.md`. Questions about
the specification gaps are especially useful. **Never post real patient data**
in issues or pull requests; see `SECURITY.md`.

## Licence and third-party material

The kit is licensed under Apache-2.0 (`LICENSE`, `NOTICE`). It uses but does
not redistribute the KBV, HL7 Deutschland and gematik packages and the HL7
validator; they are downloaded at setup (`THIRD_PARTY.md`). The source
contains LOINC codes and SNOMED CT codes that the KBV profiles require. Use of
SNOMED CT needs a licence: in Germany through the national release centre at
BfArM; elsewhere check your country's terms.

Maintained by [Omesh Kumar](https://github.com/Omesh-DH).
