# Status

Last updated: 2026-11-11.

## Phase

Foundations (archetype A mental health, archetype B metabolic) and the
workflow scaffold, reviewed by fhir-reviewer (no blockers; should-fix 1, 3, 4, 5 fixed). Exit check: the gate is clean on both golden bundles. **Met.**

## Gate

HL7 FHIR validator 6.5.28, `-tx n/a`, packages from `spec/packages/`
(kbv.mio.diga 1.1.0, kbv.basis 1.3.0, de.basisprofil.r4 1.3.2):
**0 errors, 206 warnings** on 2 golden bundles (research/metrics.csv). The
negative control is rejected as expected (`pytest -m validator`).

## Done

- Mappers: Patient, Device_DIGA, DeviceDefinition_DIGA,
  Organization_Manufacturer, Observation_Body_Weight, Questionnaire,
  QuestionnaireResponse, Observation_Score_or_Assessment_by_Scale (PHQ-9),
  Composition (Fragebögen, Befunde/Vitalzeichen, Beurteilungen), Bundle.
  10/44 profiles (docs/spec-inventory.md).
- Spec pinned with sha256 (spec/packages.lock.json). The validator loads only these.
- Validator bisection and pin (docs/decisions/0004). Spec gaps G1–G5 (docs/gaps.md).
- Ground-truth check of project assumptions (docs/decisions/0005).
- Workflow: CLAUDE.md, /new-mapper, /fix-validation, /spec-check, /status,
  agents fhir-reviewer, regulatory-researcher, thesis-writer.

## Open

- Archetypes C (tinnitus) and D (musculoskeletal): pick the data and profiles
  (likely Diary_Entry, Procedure_Activity, Functional_Assessment, Goal).
- Provenance: `agent.type` has a required binding still to map.
- `epa_import/` stub over `de.gematik.epa.medication` 1.3.5 (read side only).
- Patient name (KBV name datatype needs the `humanname-own-name` extension).
- Optional: a 1.0.0-festlegung pack plus a non-blocking Referenzvalidator run, for the
  thesis comparison (decision 0001).
- Replace the placeholder `KIT_CANONICAL_BASE` (`https://diga-epa-kit.example/fhir`) with a URL the project controls before any real export (decision 0006).
- `Device.version` (must-support): add an optional DiGA version to the input (fhir-reviewer #7).
- Score referenceRange is the scale bounds, not a normal range; consider `referenceRange.type` (fhir-reviewer #8).
- Cost model and interview guide (research/).
- Thesis: binding MIO version for ePA export. Ask the regulatory-researcher.

## Effort

See research/timelog.csv. Hours for 2026-11-02 not yet filled in.
