# 0005 Ground-truth check of project assumptions

Date: 2026-11-02. Status: record. Re-run with `/spec-check`.

Checked against the live registries (Simplifier package feed, GitHub API):

| Claim | Result |
| --- | --- |
| Latest MIO DiGA is 1.1.0 | Confirmed. Versions published: 1.0.0(-kommentierung, -benehmensherstellung, -festlegung), 1.1.0(-kommentierung, -benehmensherstellung); `latest` = 1.1.0. Nothing newer. |
| Referenzvalidator 2.16.x, DiGA via external `diga` plugin | Confirmed: CLI 2.16.6. The only DiGA plugin release is `diga-0.10.0` (2023-12-21), and it targets **1.0.0-festlegung**. No plugin for 1.1.0. |
| Device must carry VE-ID and PZN | Confirmed by the profile: `Device.identifier` (type.text `DiGA-VE-ID`) min 1, `Device.type.coding:pznCode` min 1. |
| "Core profiles" list | Incomplete for 1.1.0: 44 profiles. The 9 vital-sign Observations, Questionnaire/Response, Patient, Medication*, Goal and Procedure_Activity are also section targets (docs/spec-inventory.md). |
| mio42 validation package as test material | **Corrected 2026-11-11.** The first check looked at the wrong repository (`Austauschplattform-MIO-DiGA-Beispieldateien`, README only). The package the plan names, `mio42-GmbH/Validierungspaket-MIO-DiGA-Toolkit` (last push 2024-12-05, no licence on the repo), holds three full example bundles for 1.1.0 and a minimal and maximal example per profile, as XML. Usable as downloaded test input; not to be committed. |
| ePA→DiGA medication carrier | Not MIO DiGA. gematik `de.gematik.epa.medication` (latest 1.3.5, 1.4.0-ballot.1 in progress). `epa_import/` reads that model and maps into MIO DiGA `Medication` / `MedicationStatement_Medication_Information` only for re-export. |

Not verified here (legal and press sources): GeDIG dates and content, the ePA
3.x XDS/VAU/HealthID transport description, industry statements. These go
to the `regulatory-researcher` agent, with primary sources.
