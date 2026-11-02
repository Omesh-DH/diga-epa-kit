# 0005 Ground-truth check of project assumptions

Date: 2026-11-02. Status: record. Re-run with `/spec-check`.

Checked against the live registries (Simplifier package feed, GitHub API):

| Claim | Result |
| --- | --- |
| Latest MIO DiGA is 1.1.0 | Confirmed. Versions published: 1.0.0(-kommentierung, -benehmensherstellung, -festlegung), 1.1.0(-kommentierung, -benehmensherstellung); `latest` = 1.1.0. Nothing newer. |
| Referenzvalidator 2.16.x, DiGA via external `diga` plugin | Confirmed: CLI 2.16.6. The only DiGA plugin release is `diga-0.10.0` (2023-12-21), and it targets **1.0.0-festlegung**. No plugin for 1.1.0. |
| Device must carry VE-ID and PZN | Confirmed by the profile: `Device.identifier` (type.text `DiGA-VE-ID`) min 1, `Device.type.coding:pznCode` min 1. |
| "Core profiles" list | Incomplete for 1.1.0: 44 profiles. The 9 vital-sign Observations, Questionnaire/Response, Patient, Medication*, Goal and Procedure_Activity are also section targets (docs/spec-inventory.md). |
| mio42 validation package as test material | `mio42-GmbH/Austauschplattform-MIO-DiGA-Beispieldateien` holds only a README (last push 2022-06, no licence). Not usable. |
| ePA→DiGA medication carrier | Not MIO DiGA. gematik `de.gematik.epa.medication` (latest 1.3.5, 1.4.0-ballot.1 in progress). `epa_import/` reads that model and maps into MIO DiGA `Medication` / `MedicationStatement_Medication_Information` only for re-export. |

Not verified here (legal and press sources): GeDIG dates and content, the ePA
3.x XDS/VAU/HealthID transport description, industry statements. These go
to the `regulatory-researcher` agent, with primary sources.
