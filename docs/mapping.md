# DiGA data → MIO DiGA 1.1.0 profiles

Seed for sub-question 1. Section slices and allowed entry profiles come
straight from `KBV_PR_MIO_DIGA_Composition|1.1.0`.

| DiGA data | Composition section (slice) | Profile(s) | Library |
| --- | --- | --- | --- |
| Body weight | befundeUndErgebnisse → vitalzeichenUndKoerpermasse | Observation_Body_Weight | done |
| Blood pressure, heart rate, glucose, SpO₂, temperature, height, resp. rate | befundeUndErgebnisse → vitalzeichenUndKoerpermasse | Observation_Blood_Pressure, _Heart_Rate, _Glucose_Concentration, _Peripheral_Oxygen_Saturation, _Body_Temperature, _Body_Height, _Respiratory_Rate | – |
| Other results | befundeUndErgebnisse | Observation_Free | – |
| PROMs / questionnaires | frageboegen | Questionnaire, QuestionnaireResponse | PHQ-9 done |
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

One `Questionnaire` per instrument (identified by `code` = LOINC panel
44249-1, no `title`, because invariant ques-1 allows only one of the two;
`url` = `http://loinc.org/q/44249-1`). Each completion yields a
`QuestionnaireResponse` (answers as LOINC LA codes) plus a score
`Observation` (LOINC 44261-6, category `survey`, `{score}` quantity,
`derivedFrom` the response, `referenceRange` 0–27 without `text`, which the
profile prohibits). Questionnaire and responses go in *Fragebögen*, scores in
*Beurteilungen*. Item texts are LOINC displays, not the licensed German
wording; new instruments are added to `instruments.py`.
