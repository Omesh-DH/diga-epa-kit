# diga-epa-kit

Open-source kit that turns typical DiGA data into KBV **MIO DiGA 1.1.0**
FHIR R4 document bundles for the ePA, with a validation gate in CI. Part of
a thesis on the interoperability cost of DiGA for small manufacturers.

Status: early. Two archetypes are mapped end to end:

| Archetype | Data | Profiles |
| --- | --- | --- |
| A, mental health | PHQ-9 total scores, mood diary | Observation_Score_or_Assessment_by_Scale, Observation_Diary_Entry |
| D, exercise | Goals, exercise plan, adherence diary | Goal, CarePlan, Observation_Diary_Entry |
| B, metabolic | Body-weight and blood-pressure series | Observation_Body_Weight, Observation_Blood_Pressure |

Every bundle also carries Patient, Device_DIGA (VE-ID and PZN),
DeviceDefinition_DIGA and Organization_Manufacturer. See
`docs/spec-inventory.md` for coverage and `docs/gaps.md` for spec-level
findings.

## Use

```bash
python -m venv .venv && .venv/bin/pip install -e ".[dev]"
python scripts/fetch_spec.py          # pinned FHIR packages into spec/packages/
diga-epa-kit build synthetic/archetype_a_mental/phq9_three_months.json -o out/phq9.json
diga-epa-kit check out/phq9.json      # fast in-process checks
python scripts/validate.py out/phq9.json   # HL7 FHIR validator, needs Java 17+
```

The input is plain JSON validated by a pydantic model (`src/diga_epa_kit/input/model.py`).
It needs no FHIR knowledge.

## Develop

`make test`, `make golden`, `make validate`, `make inventory` (see CLAUDE.md
for the Windows equivalents). The working loop, slash commands and review
agents are described in `CLAUDE.md` and `.claude/`.

## Licence

Apache-2.0. Example data is synthetic. Third-party specifications and
terminologies are fetched, not redistributed (THIRD_PARTY.md).
