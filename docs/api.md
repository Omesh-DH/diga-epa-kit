# API reference

Everything a caller needs is importable from `diga_epa_kit`.

## Python

| Name | What it does |
| --- | --- |
| `DigaExport` | The input model (pydantic). `DigaExport.model_validate(dict)` or `.model_validate_json(text)` checks the data and raises `pydantic.ValidationError` with the offending field. |
| `build_bundle(data, version=DEFAULT_VERSION, now=None) -> dict` | Turns a `DigaExport` into one MIO DiGA document Bundle as a plain dict. `now` is the export time (default: current UTC time); pass it to get reproducible output. Resource ids are deterministic. |
| `check_bundle(bundle) -> list[str]` | Fast structural checks in-process. An empty list means no problem found. Not a substitute for the validator. |
| `validate(bundles, *, jar, packages, tx="n/a", tx_cache=None, report_path=None) -> Report` | Runs the HL7 FHIR validator on one or more bundles (dicts or file paths). The caller passes the validator jar and the profile packages. Raises `ValidatorUnavailable` without Java or when the validator crashes. |
| `Report` | `.errors`, `.warnings`, `.timeouts` (lists of `Issue` with `severity`, `code`, `location`, `message`), `.conclusive` (false after a timeout) and `.ok`. |
| `DEFAULT_VERSION` | The MIO DiGA version the kit targets ("1.1.0"). |

```python
import json
from diga_epa_kit import DigaExport, build_bundle, check_bundle

data = DigaExport.model_validate_json(open("my-export.json", encoding="utf-8").read())
bundle = build_bundle(data)
assert check_bundle(bundle) == []
json.dump(bundle, open("bundle.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
```

Also available: `diga_epa_kit.explain.explain(message)` returns a title, a
text and whether the finding concerns the bundle at all.

## Command line

| Command | What it does | Exit code |
| --- | --- | --- |
| `diga-epa-kit build INPUT [-o FILE]` (alias `convert`) | Input JSON to Bundle | 0 ok, 1 local check failed, 2 invalid input |
| `diga-epa-kit check BUNDLE` | Fast local checks | 0 ok, 1 problems |
| `diga-epa-kit schema [-o FILE]` | JSON Schema of the input | 0 |
| `diga-epa-kit validate BUNDLE... --jar JAR --ig PKG... [--explain]` | HL7 FHIR validator | 0 ok, 1 errors, 3 validator unavailable, 4 inconclusive (timeout) |
| `diga-epa-kit explain-error MESSAGE` or `--report FILE` | Plain-language explanation | 0, 2 without input |

## Input fields

The authoritative list with types and limits is `docs/input-schema.json`
(a test keeps it in step with the code). Which field becomes which
resource:

| Input field | Resource and profile |
| --- | --- |
| `diga` | Device_DIGA, DeviceDefinition_DIGA, Organization_Manufacturer |
| `patient` | Patient |
| `period_start`, `period_end` | Composition (Betrachtungszeitraum) |
| `body_weights`, `body_heights`, `blood_pressures` | Observation_Body_Weight, _Body_Height, _Blood_Pressure |
| `heart_rates`, `body_temperatures`, `oxygen_saturations`, `respiratory_rates` | Observation_Heart_Rate, _Body_Temperature, _Peripheral_Oxygen_Saturation, _Respiratory_Rate |
| `glucose_readings` | Observation_Glucose_Concentration |
| `body_mass_indices`, `daily_steps` | Observation_Free |
| `prom_scores` | Observation_Score_or_Assessment_by_Scale (scores only, no questionnaire wording) |
| `diary_entries` | Observation_Diary_Entry |
| `goals`, `care_plans` | Goal, CarePlan |

The reasoning behind each mapping is in docs/mapping.md.
