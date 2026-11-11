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
| PROM scores (PHQ-9, GAD-7 …) | beurteilungen | Observation_Score_or_Assessment_by_Scale (PHQ-9 total), Observation_Functional_Assessment | PHQ-9 done |
| Diary entries | patientenberichte | Observation_Diary_Entry | – |
| Exercises, sessions | aktivitaeten | Procedure_Activity | – |
| Food intake | nahrung | Observation_Nutrition_Intake | – |
| Lifestyle (smoking, alcohol, sleep) | lebensstilfaktoren | Observation_Life_Style_Factor | – |
| Environmental factors | umweltfaktoren | Observation_Environmental_Factor | – |
| Goals, therapy plan | ziele | Goal, CarePlan | – |
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
