# diga-epa-kit

Open-source kit that turns typical DiGA data into KBV **MIO DiGA 1.1.0**
FHIR R4 document bundles for the ePA, with a validation gate in CI. Part of
a thesis on the interoperability cost of DiGA for small manufacturers.

Status: early. Four archetypes produce a bundle that passes the validator; none is complete:

| Archetype | Data | Profiles |
| --- | --- | --- |
| A, mental health | PHQ-9 and GAD-7 total scores, mood diary | Observation_Score_or_Assessment_by_Scale, Observation_Diary_Entry |
| C, pain | 0–10 pain ratings, diary | Observation_Score_or_Assessment_by_Scale, Observation_Diary_Entry |
| D, exercise | Goals, exercise plan, adherence diary | Goal, CarePlan, Observation_Diary_Entry |
| B, metabolic | Body-weight and blood-pressure series, body height, heart rate, temperature, oxygen saturation (pulse oximeter), respiratory rate, glucose, BMI, daily steps, goals, medication (also read from an ePA medication list) | Observation_Body_Weight, Observation_Body_Height, Observation_Blood_Pressure, Observation_Heart_Rate, Observation_Body_Temperature, Observation_Peripheral_Oxygen_Saturation, Observation_Respiratory_Rate, Observation_Glucose_Concentration, Observation_Free, Goal, Medication, MedicationStatement_Medication_Information |

Every bundle also carries Patient, Device_DIGA (VE-ID and PZN),
DeviceDefinition_DIGA and Organization_Manufacturer. See
`docs/spec-inventory.md` for coverage and `docs/gaps.md` for spec-level
findings.

## Try it in your browser

`site/` is a page that runs the kit itself in the browser (Python via Pyodide), so
input data never leaves the visitor's computer. Pick a synthetic example or paste
your own input, build a bundle, see what the local checks say and download it; or
read an ePA medication list. It does not run the official HL7 validator.

- Online: https://omesh-dh.github.io/diga-epa-kit/ (published by
  `.github/workflows/pages.yml` once the repository is public)
- Locally: `python scripts/build_site.py`, then
  `python -m http.server 8765 --directory site` and open http://localhost:8765

### Usage counting

To learn whether the page works for people, it can count anonymous events:
page opened, kit loaded or failed to load, and whether each build or import
worked or failed, with the top-level field names and error types of the
failures (for example `build-rejected:patient:missing`). It never sends the
input, values, names or the bundle, sets no cookies, and stops when the
visitor switches it off or the browser sends Do Not Track or Global Privacy
Control. Every failure also offers a "Report this problem on GitHub" link
that opens a pre-filled issue without the input.

Counting is off until the repository variable `GOATCOUNTER_URL` holds a
GoatCounter count address (`https://CODE.goatcounter.com/count`); the Pages
workflow passes it to `scripts/build_site.py`. The counts then appear in the
GoatCounter dashboard.

## Use

```bash
python -m venv .venv && .venv/bin/pip install -e ".[dev]"
python scripts/fetch_spec.py          # pinned FHIR packages into spec/packages/
diga-epa-kit build synthetic/archetype_a_mental/phq9_three_months.json -o out/phq9.json
diga-epa-kit check out/phq9.json      # fast in-process checks
python scripts/validate.py out/phq9.json   # HL7 FHIR validator, needs Java 17+
```

The input is plain JSON validated by a pydantic model (`src/diga_epa_kit/input/model.py`).
It needs no FHIR knowledge. Step by step: `docs/quickstart.md`. Functions,
commands and input fields: `docs/api.md`; the input format as JSON Schema:
`docs/input-schema.json`.

```bash
diga-epa-kit schema                    # the input format
diga-epa-kit explain-error "Device.identifier: minimum required = 1, but only found 0"
diga-epa-kit import-medication synthetic/epa_import/medication_list.json   # ePA medication list to kit input
```

## Develop

`make test`, `make golden`, `make validate`, `make inventory` (see CLAUDE.md
for the Windows equivalents). The working loop, slash commands and review
agents are described in `CLAUDE.md` and `.claude/`.

## Licence

Apache-2.0. Example data is synthetic. Third-party specifications and
terminologies are fetched, not redistributed (THIRD_PARTY.md).
