# DiGA data → MIO DiGA 1.1.0 profiles

Seed for sub-question 1. Section slices and allowed entry profiles come
straight from `KBV_PR_MIO_DIGA_Composition|1.1.0`.

| DiGA data | Composition section (slice) | Profile(s) | Library |
| --- | --- | --- | --- |
| Body weight | befundeUndErgebnisse → vitalzeichenUndKoerpermasse | Observation_Body_Weight | done |
| Blood pressure | befundeUndErgebnisse → vitalzeichenUndKoerpermasse | Observation_Blood_Pressure | done |
| Heart rate, glucose, SpO₂, temperature, height, resp. rate | befundeUndErgebnisse → vitalzeichenUndKoerpermasse | Observation_Heart_Rate, _Glucose_Concentration, _Peripheral_Oxygen_Saturation, _Body_Temperature, _Body_Height, _Respiratory_Rate | – |
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
