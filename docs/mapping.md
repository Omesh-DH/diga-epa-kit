# DiGA data → MIO DiGA 1.1.0 profiles

Seed for sub-question 1. Section slices and allowed entry profiles come
straight from `KBV_PR_MIO_DIGA_Composition|1.1.0`.

| DiGA data | Composition section (slice) | Profile(s) | Library |
| --- | --- | --- | --- |
| Body weight | befundeUndErgebnisse → vitalzeichenUndKoerpermasse | Observation_Body_Weight | done |
| Blood pressure | befundeUndErgebnisse → vitalzeichenUndKoerpermasse | Observation_Blood_Pressure | done |
| Body height | befundeUndErgebnisse → vitalzeichenUndKoerpermasse | Observation_Body_Height | done |
| Heart rate, SpO₂, temperature, resp. rate | befundeUndErgebnisse → vitalzeichenUndKoerpermasse | Observation_Heart_Rate, _Peripheral_Oxygen_Saturation, _Body_Temperature, _Respiratory_Rate | done |
| Glucose | befundeUndErgebnisse → vitalzeichenUndKoerpermasse | Observation_Glucose_Concentration | done (no trend, no target range) |
| Other results | befundeUndErgebnisse | Observation_Free | BMI and daily step count done |
| PROM answers / questionnaires | frageboegen | Questionnaire, QuestionnaireResponse | not exported (decision 0007) |
| PROM scores (PHQ-9, pain scale, GAD-7 …) | beurteilungen | Observation_Score_or_Assessment_by_Scale, Observation_Functional_Assessment | PHQ-9 total, GAD-7 total, 0–10 pain rating and ODI score done; Functional_Assessment blocked (decision 0008) |
| Diary entries | patientenberichte | Observation_Diary_Entry | done |
| Exercises, sessions | aktivitaeten | Procedure_Activity | – |
| Food intake | nahrung | Observation_Nutrition_Intake | – |
| Lifestyle (smoking, alcohol, sleep) | lebensstilfaktoren | Observation_Life_Style_Factor | – |
| Environmental factors | umweltfaktoren | Observation_Environmental_Factor | – |
| Goals, therapy plan | ziele | Goal, CarePlan | done (free text) |
| Problems, allergies | probleme | Condition_Problem, AllergyIntolerance | – |
| Medication, intake log | medikation | MedicationStatement_Medication_Information, MedicationAdministration_Medication_Intake | – |
| Appointments | termineBegegnungen | Appointment, Encounter | – |
| Attachments (PDF reports) | anhaenge | DocumentReference | – |
| Care contacts | kontakte | PractitionerRole, Practitioner, RelatedPerson, Organization | – |

Always present, outside the sections: Patient, Device_DIGA (Composition
author, DiGA-VE-ID + PZN), DeviceDefinition_DIGA, Organization_Manufacturer.
Provenance can target almost every profile but is not referenced from a
section.

## PROM pattern (PHQ-9)

Scores and codes only (decision 0007). Each completion yields one score
`Observation` (LOINC 44261-6, category `survey`, `{score}` quantity,
`referenceRange` = the scale's bounds, `device` = the DiGA) in *Beurteilungen*. No Questionnaire,
no QuestionnaireResponse, no item codes or wording. Two must-support
elements are deliberately left empty: `derivedFrom` (there is no response to
point at) and `interpretation` (severity bands are the instrument author's,
not the kit's, to assert). New instruments are
added to `terminology/instruments.py` with their total-score code and range.

## Blood pressure pattern

One `Observation` per reading: panel code LOINC 85354-9 plus SNOMED 75367002,
no `Observation.value` (the base profile prohibits it), and two components,
systolic (8480-6, 271649006) and diastolic (8462-4, 271650006), each a
quantity with unit text `mm Hg` and UCUM code `mm[Hg]`. Codes come from
`VitalSignDE_Blutdruck` (de.basisprofil.r4), displays and SNOMED codings
from `KBV_PR_Base_Observation_Blood_Pressure` (kbv.basis). The optional mean
component, `method`, `bodySite`, `device` and `note` are must-support but not
filled: the input does not carry them.

## Diary entry pattern

One `Observation` per entry in *Patientenberichte*: code LOINC 51855-5
"Patient Note" (the profile's pattern), `effectiveDateTime` = when the
patient wrote it, `valueString` = the text, verbatim. The profile prohibits
`category`, `method`, `device`, `bodySite` and `component`. Not filled:
`effectivePeriod`, `note` and `hasMember` (links from an entry to other
observations); the input does not carry them. The section code comes from
KBV's own `KBV_CS_MIO_DIGA_Section_Codes`, not SNOMED CT.

Diary text is free text written by the patient. It is the one place where
the export carries unstructured personal content, so a manufacturer has to
decide per DiGA whether it belongs in the ePA document. The kit caps an
entry at 5000 characters and rejects control characters; those limits are
the kit's, not the profile's. Two entries with the same timestamp are also
rejected, because the resource id is derived from it.

## Goal and care plan pattern

Both sit in *Ziele*, goals first, then plans.

- `Goal`: `lifecycleStatus`, `description.text`, `startDate` and, if the
  goal has an end date, the `KBV_EX_Base_Treatment_Goal_End` extension. Free
  text only. `target` is left out: the end-date extension already carries
  the date, and a target needs a `measure` the input does not have.
- `CarePlan`: `status`, `intent` = `plan` (profile pattern), `title`, `goal`
  references, and one `activity.detail` per planned activity with `status`,
  `description`, an optional `scheduledPeriod` and the patient as `performer`.

`Goal.expressedBy` and `CarePlan.author` are filled with the patient only
when the input says so (`set_by_patient`, `written_by_patient`). Both allow
only a person as target, not the DiGA (gaps G8). Not filled: achievement
status (a completed goal does not say whether it was reached; the codes
belong to the FHIR core package, which is not among the pinned packages),
priority, outcome, notes, and the coded parts of an activity.

Statuses have no default. A plan that is completed or revoked must not have
open activities, and nothing may start after the end of the period.

The DiGA's own keys for goals and plans (`id`) only link plans to goals
inside the input. They are not exported.

## Pain rating (archetype C)

A 0–10 pain rating is one more instrument in `terminology/instruments.py`:
LOINC 72514-3, range 0–10, exported exactly like a PHQ-9 total. The anchor
texts of the scale are not carried. The functional score is the Oswestry
Disability Index (LOINC 97909-6), exported as its percentage 0–100, also as
a scale score: the Functional_Assessment profile is blocked (decision
0008). The input takes a whole percentage: with unanswered sections the
index can be fractional, and the DiGA rounds it before export, because the
kit does not pick a rounding rule. No severity band is exported; the bands are the instrument's to
assert. Where the pain is (`bodySite`,
must-support) is not exported: the input has no field for it.

## Reference range of a score

`referenceRange` holds the bounds of the scale (0–27, 0–10, 0–100), not a
normal range. KBV's own example bundle does the same: a pain score of 6 with
an untyped range 1–10. Because a bare range can be read as "normal", the kit
adds `referenceRange.type.text` = "Wertebereich der Skala". The profile
prohibits `referenceRange.text`, and the kit sets no `type.coding`: the
range-meaning codes describe normal, recommended or therapeutic ranges, none
of them "possible values", and that code system is not in the pinned
packages.

## GAD-7 (archetype A)

The GAD-7 total is one more instrument in `terminology/instruments.py`:
LOINC 70274-6, range 0–21, exported exactly like a PHQ-9 total and in the
same section. No severity band and no item answers are exported.

## Free results: BMI and daily steps (archetype B)

`KBV_PR_MIO_DIGA_Observation_Free` constrains almost nothing: it fixes the
profile, prohibits a few elements (`meta.source/security/tag`,
`implicitRules`, `language`, `contained`, `specimen`) and narrows reference
targets. It has no code pattern, no identifier slice and no must-support
element. The Composition allows it only as a direct entry of "Befunde und
Ergebnisse", not in the Vitalzeichen subsection. What the kit emits is
therefore its own choice:

- **BMI**: LOINC 39156-5, `valueQuantity` in `kg/m2` rounded to one decimal,
  `effectiveDateTime` = the time of the weight reading the BMI is based on
  (not the time of the calculation), category `vital-signs`.
  The category is not optional: FHIR R4 makes the validator apply the core
  bmi profile whenever it sees this code. `device` = the DiGA and no
  performer, because the value is calculated, not measured. No `derivedFrom`
  to weight and height: the input does not say which readings were used.
- **Daily steps**: LOINC 41950-7 (steps in 24 hours), category `activity`,
  `effectiveDateTime` = the calendar day without a time, `valueQuantity` with
  UCUM `{#}/(24.h)` as in LOINC's example units, performer = the patient. The
  phone or wearable that counted is not exported: the input does not name it.
  "In 24 hour" is read as "per calendar day"; the day of a clock change has
  23 or 25 hours. Days without data must be left out of the input: a 0 is
  exported as a real count of zero steps.
- Neither carries the `identifier` that the specific profiles require; the
  free profile has no such slice.

The gate does not confirm the unit. Its message (2026-11-12): "Unable to
validate code '{#}/(24.h)' in system 'http://unitsofmeasure.org' because
the validator is running without terminology services" (a warning). The
code is the example unit shown on loinc.org/41950-7 (read 2026-11-12).

## DiGA software version

`diga.version` (optional) becomes `Device.version` on the Device_DIGA
resource: `value` = the label as the manufacturer writes it, `type.text` =
"Softwareversion". The profile makes `version` must-support and `type`
required once a version is given; `type.coding` is optional and, if used,
needs system, version, code and display. The kit sets no coding: neither
KBV profile binds a value set to `type`, FHIR R4 core has none either, and
the pinned packages name no code for "software version" (the only package example, kbv.basis `examples/device.json`, puts
the resource-identifier code there, which does not describe a version).
`DeviceDefinition.version` is prohibited in DeviceDefinition_DIGA, so the
version appears on the Device only. The version is not part of any resource
id: an app update does not turn the same DiGA into a new device. The input
holds one version per export; if the app was updated inside the period, the
manufacturer chooses which one to state. The profile would allow several
versions but cannot say which one produced which data.

- "Softwareversion" is the kit's own wording, not taken from a package.
- The field is optional. Leaving it out leaves a must-support element empty,
  so a manufacturer should always fill it.
- Accepted labels use letters, digits and `. + _ -`; a build number goes in
  as `2.4.1+57`, not `2.4.1 (57)`.
- Two exports of one DiGA with different app versions carry a Device with
  the same id and different content. A reader that de-duplicates resources
  by id across documents must expect that (gap G12).

## Body height

`body_heights` maps to `KBV_PR_MIO_DIGA_Observation_Body_Height`, built like
body weight: LOINC 8302-2 "Body height" (de.basisprofil.r4 value set
VitalSignDE_Body_Height_Loinc) plus SNOMED 1153637007 "Body height
(observable entity)" (kbv.basis KBV_VS_Base_Body_Height_SNOMED_CT),
`valueQuantity` in `cm` rounded to one decimal, performer = the patient,
in the Vitalzeichen subsection. The general SNOMED concept is used because
the input does not say whether the patient stood or lay down. No `method`:
unlike body weight, no value set for it exists in the packages.

A height may be older than the export period, because apps usually ask for
it once at the start of use; it only must not lie after the period end.
This is the one measurement exempt from the "inside the period" rule (goals
and plans may also start earlier). The packages do not say whether entries
must lie inside the period (gap G13). For a typed-in height `measured_at`
is in practice the time of entry; the input does not distinguish measured
from typed-in, and the packages have no code for that. The
BMI still has no `derivedFrom` to weight and height: the input does not
say which readings a BMI was calculated from.

## Heart rate, body temperature, oxygen saturation, respiratory rate

Four profiles with the same shape: one value, one unit, performer = the
patient, in the Vitalzeichen subsection. One table in `mappers/vitals.py`
holds what differs:

| Input | Profile | LOINC | SNOMED | Unit text / UCUM |
| --- | --- | --- | --- | --- |
| `heart_rates` (bpm) | Observation_Heart_Rate | 8867-4 Heart rate | 364075005 | per minute / `/min` |
| `body_temperatures` (celsius) | Observation_Body_Temperature | 8310-5 Body temperature | 386725007 | Celsius / `Cel` |
| `oxygen_saturations` (percent) | Observation_Peripheral_Oxygen_Saturation | 2708-6 Oxygen saturation in Arterial blood | 431314004 | % / `%` |
| `respiratory_rates` (per_minute) | Observation_Respiratory_Rate | 9279-1 Respiratory rate | 86290005 | per minute / `/min` |

Sources: the LOINC code is a pattern in the de.basisprofil.r4 VitalSignDE
profile, the LOINC display and the unit text are patterns in the kbv.basis
profile, the UCUM code is a de.basisprofil.r4 pattern, and the SNOMED
coding is the kbv.basis value set (heart rate, temperature, respiratory
rate) or pattern (oxygen saturation).

- Where a SNOMED value set offers several concepts (heart rate at a
  systemic artery, temperature by body site), the general concept is used:
  the input does not say how or where the value was taken. `bodySite` and
  `method` stay empty for the same reason.
- Oxygen saturation is the exception: kbv.basis requires `method` and fixes
  it to "Pulse oximeter" (448703006). The profile therefore fits only
  pulse-oximeter readings, which the input model states (gap G14).
- Temperature is rounded to one decimal with Python's `round` (binary
  floats, so 36.65 becomes 36.6); the three rates are whole numbers.
- Glucose needs more than one value and has its own section ("Glucose").

## Size and speed

`scripts/bench_one_year.py` builds one synthetic patient with a year of
daily weight, blood pressure, heart rate and steps plus weekly BMI,
fortnightly PHQ-9 and GAD-7, three diary entries a week, a height and two
goals. Measured on 2026-11-14 on the development laptop (one run of the
validator, three of the build):

| Measure | Result |
| --- | --- |
| Resources | 1,731 |
| Bundle size | 2.6 MB (JSON, not indented) |
| Input check + build + local checks + serialisation | about 0.15 s |
| HL7 validator 6.5.28, offline | 232 s, of which 57 s loading the packages and 170 s validating |
| Validator result | 0 errors, 15,538 warnings, no timeout |

The kit is not the bottleneck; the validator is, at roughly 0.1 s per
resource. Not tested: whether an ePA accepts a document of this size, and
memory use on a small CI runner (the validator peaked at 3 GB here).

## Glucose

`glucose_readings` maps to `KBV_PR_MIO_DIGA_Observation_Glucose_Concentration`,
in the Vitalzeichen subsection, performer = the patient. Each reading states
its value, its unit, what was measured and, for blood readings, optionally
when:

| Input | Becomes | Source in kbv.basis |
| --- | --- | --- |
| `specimen` + `unit` | LOINC code. Blood: 2339-0 (mg/dL) or 15074-8 (mmol/L). Interstitial fluid: 2344-0 (mg/dL) or 14745-4 (mmol/L) | KBV_VS_Base_Glucose_Concentration_LOINC (required) |
| `specimen` | SNOMED code. Blood: 434912009. Interstitial fluid: 434910001 | KBV_VS_Base_Glucose_Concentration_SNOMED_CT (required) |
| `unit` | `valueQuantity.unit` and `.code`: `mg/dL` or `mmol/L` | KBV_VS_Base_Glucose_Concentration_Unit (required). The unit text is the UCUM code, as the package example does for mg/dL |
| `context` (blood only, optional) | `method`: fasting 271062006, before_lunch 271063001, before_supper 271064007, before_bed 271065008, after_meal 302788006, random 271061004 | KBV_VS_Base_Glucose_Concentration_Method_SNOMED_CT (extensible) |
| `specimen` = interstitial fluid | `method` 359776002 on every such reading | same value set |
| `outside_measuring_range` (optional) | `valueQuantity.comparator`: below is `<`, above is `>`; `value` is then the device's measuring limit. The same statement in words in `note.text` | FHIR R4 `Quantity.comparator`; the glucose profiles do not constrain it (gap G16) |

- **Code pairing.** Which LOINC code goes with which SNOMED code follows the
  kbv.basis concept map `KBV_CM_Base_Terminology_Complete_German`. It maps
  the "Body fluid" LOINC codes and the interstitial-fluid concept to one
  German concept (tissue glucose) and the "Blood" codes and the blood
  concept to the other. No profile rule enforces the pairing (gap G15).
- **Context names.** The same concept map gives the method codes their
  German meaning, and the input names follow it: the SNOMED "lunch time",
  "supper time" and "bedtime" concepts mean *before* lunch, supper and
  going to bed. All six are blood measurements, so `context` is rejected
  for sensor readings.
- **Sensor readings.** The concept map reads 359776002 as continuous glucose
  monitoring (CGM). Interstitial fluid is measured that way, so the kit
  states this method for every sensor reading and never for a blood
  reading. The caller cannot choose it.
- **Units.** The unit is never converted: a reading is exported in the unit
  the app holds, and the LOINC code follows it. The limits (10–1000 mg/dL,
  0.5–56 mmol/L) are plausibility limits, not clinical ones, and they
  overlap: any number from 10 to 56 is accepted in either unit. A wrong
  unit is caught only outside that window. Inside it, 12 mmol/L (high)
  labelled mg/dL is exported as 12 mg/dL (dangerously low), and 45 mg/dL
  (low) labelled mmol/L as 45 mmol/L (dangerously high). A whole data set
  with the wrong unit nearly always has a value outside the window and is
  rejected; a single mislabelled reading is not. No limit can close the
  window, so the manufacturer must get the unit right.
- **LO and HI.** Outside their measuring range meters and sensors show
  "LO" or "HI" instead of a number. The profile requires a value and
  prohibits `dataAbsentReason`, so such a reading is exported as below or
  above the device's measuring limit: `outside_measuring_range` = `below`
  or `above` with `value` = that limit becomes `valueQuantity.comparator`
  `<` or `>`. The manufacturer supplies the limit; the kit knows no device.
  - The field is about the device, not the patient's target range. A value
    that is merely too low or too high for the patient is a plain value.
    No rule can tell the two apart: 62 mg/dL "below" would be accepted.
  - The limit is the lowest or highest number the device still shows, so
    `<` and `>` are right and `<=` and `>=` are not. It takes at most one
    decimal; the kit does not round a limit.
  - A lower limit must be at most 100 mg/dL (5.6 mmol/L) and an upper limit
    at least 200 mg/dL (11.1 mmol/L). These are the kit's own plausibility
    rules. They reject a swapped direction ("above 40") and a limit given
    in the other unit. Both mistakes together can pass: a true "below 40
    mg/dL" entered as "above 40 mmol/L" is accepted.
  - In FHIR R4 the comparator is a modifier element: a receiver that
    ignores it reads "below 40 mg/dL" as "40 mg/dL" (gap G16). The kit
    therefore repeats the statement in words in `note.text`, for example
    "Außerhalb des Messbereichs des Geräts: unter 40 mg/dL." The wording is
    the kit's own.
  - Still not exportable: a reading with no value at all, such as a sensor
    error, and a LO or HI whose limit the manufacturer does not know.
- **Rounding.** One decimal with Python's `round` (binary floats, so 5.55
  becomes 5.5). A whole number given as an integer stays an integer.
- **Same minute.** A meter and a sensor reading at the same time are two
  readings; the specimen is part of the resource id.
- **Not exported.** The trend (`interpretation`), a target range
  (`referenceRange`), `bodySite`, `device`, `note`, `method.text` and the
  `teilVon` extension: the input has no fields for them.
- **Volume.** Sensor data adds up. One value every 5 minutes for 90 days is
  25,920 readings: measured on 2026-11-15, the kit builds that bundle in
  about 2.3 s and it is 43.6 MB. The validator was not run on it; at the
  rate of the one-year test (about 0.1 s per resource) it would need
  roughly 42 minutes. An app with sensor data should export shorter
  periods or thinned values.
- **What checks this.** The offline gate cannot check the value-set
  bindings (warnings only). It does enforce the fixed SNOMED version of
  the method coding (gap G15) and the comparator code: `<` and `>` pass,
  and a code outside FHIR's four (tested with `LO`) is an error (gap G16).
  The validator's negative control covers both, and a comparator on a
  heart rate, where the profile prohibits it. Unit tests compare every
  code the mapper can emit, the
  pairing and the context meanings with the pinned package files; they are
  skipped where the packages are not fetched.
