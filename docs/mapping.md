# DiGA data → MIO DiGA 1.1.0 profiles

Seed for sub-question 1. Section slices and allowed entry profiles come
straight from `KBV_PR_MIO_DIGA_Composition|1.1.0`.

| DiGA data | Composition section (slice) | Profile(s) | Library |
| --- | --- | --- | --- |
| Body weight | befundeUndErgebnisse → vitalzeichenUndKoerpermasse | Observation_Body_Weight | done |
| Blood pressure | befundeUndErgebnisse → vitalzeichenUndKoerpermasse | Observation_Blood_Pressure | done |
| Heart rate, glucose, SpO₂, temperature, height, resp. rate | befundeUndErgebnisse → vitalzeichenUndKoerpermasse | Observation_Heart_Rate, _Glucose_Concentration, _Peripheral_Oxygen_Saturation, _Body_Temperature, _Body_Height, _Respiratory_Rate | – |
| Other results | befundeUndErgebnisse | Observation_Free | – |
| PROM answers / questionnaires | frageboegen | Questionnaire, QuestionnaireResponse | not exported (decision 0007) |
| PROM scores (PHQ-9, pain scale, GAD-7 …) | beurteilungen | Observation_Score_or_Assessment_by_Scale, Observation_Functional_Assessment | PHQ-9 total and 0–10 pain rating done; Functional_Assessment blocked (decision 0008) |
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
`referenceRange` 0–27 as the scale bounds and without `text`, which the
profile prohibits, `device` = the DiGA) in *Beurteilungen*. No Questionnaire,
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
texts of the scale are not carried. The archetype's functional score is
open: the instrument has not been chosen. Where the pain is (`bodySite`,
must-support) is not exported: the input has no field for it.
