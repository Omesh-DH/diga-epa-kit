# Spec gaps

Findings where the **specification itself** (profiles, pinned terminology,
tooling) prevents a clean result, so the mapper can't fix them without
breaking a profile. Each entry: what, where, evidence, and how we handle it.
Evidence for sub-question 2.

## G1 Composition.type display rejected by LOINC

- **Where**: `KBV_PR_MIO_DIGA_Composition|1.1.0`, `Composition.type.coding`
  patternCoding with display `Personal health monitoring report Document`
  (LOINC 53576-5, version 2.72).
- **Evidence**: with `-tx https://tx.fhir.org/r4` (validator 6.10.4):
  *Wrong Display Name … Valid display is one of 3 choices: 'Personal Health
  Monitoring Report' …*
- **Handling**: keep the profile's pattern. This is the only error in
  terminology-backed runs of the weight archetype.

## G2 Pinned terminology versions not served

- **Where**: patterns pin LOINC `2.72`, SNOMED CT International
  `…/version/20220331`, v2-0203 `2.9`, observation-category `4.0.1`.
- **Evidence**: tx.fhir.org serves LOINC 2.77/2.83 and v2-0203 4.0.0/5.0.0, and
  reports *could not be found, so the code cannot be validated*.
- **Handling**: those codes are effectively unchecked in every mode. Report as a
  limitation. The gematik Referenzvalidator ships its own terminology
  package (`gematik.kbv.sfhir.cs.vs`) for this reason.

## G3 Device_DIGA identifier type is text-only

- **Where**: `KBV_PR_MIO_DIGA_Device_DIGA|1.1.0`, `Device.identifier.type.text = DiGA-VE-ID`.
- **Evidence**: base binding warning *No code provided, and a code should be
  provided from the value set 'IdentifierType'*.
- **Handling**: warning only. Follow the profile.

## G4 KBV package ships without snapshots

- **Where**: all StructureDefinitions in `kbv.mio.diga#1.1.0` (differential only).
- **Evidence**: validator 6.10.4 fails to generate snapshots for
  `KBV_PR_Base_Observation_Body_Temperature` and aborts with *Slice encountered
  midway through set (path = Observation.value[x])* when it resolves the
  Beurteilungen reference against `Observation_Functional_Assessment`.
- **Handling**: validator 6.5.28 pinned (decision 0004). Whether a bundle
  "passes" depends on the validator release, which is itself a cost driver
  for manufacturers.

## G5 Required bindings fail offline on some validator versions

- **Where**: de.basisprofil.r4 `VitalSignDE_Body_Weight_Loinc` and
  `VitalSignDE_Body_Weigth_UCUM` (required) under Body_Weight.
- **Evidence**: validator 6.3.14 with `-tx n/a` reports these as **errors**
  (*code system http://loinc.org|2.72 was not found*, *http://unitsofmeasure.org
  was not found*), and the Composition entry then fails to match any allowed
  target profile. 6.10.4 reports the same situation as warnings.
- **Handling**: 6.5.28 reports them as warnings (decision 0004).

## G6 Self-reported weight method code means "usual" weight

- **Where**: kbv.basis `KBV_VS_Base_Body_Weight_Method_SNOMED_CT` (required for
  `Observation.method.coding:Datenerhebung`). It allows only 363808001
  *Measured body weight* and 786458005 *Self reported **usual** body weight*.
- **Issue**: a weight the user types into the app is a self-reported *current*
  reading, but the only non-measured code means habitual weight.
- **Handling**: map `self_reported` to 786458005 as the closest allowed code,
  and record the semantic mismatch here (found by fhir-reviewer, 2026-11-02).

## G7 Official example bundles fail the offline gate

- **Where**: the three full examples in `mio42-GmbH/Validierungspaket-MIO-DiGA-Toolkit`
  (`Example/REAL_EXAMPLE_{1,2,3}_KBV_PR_MIO_DIGA_Bundle.xml`, all `|1.1.0`).
- **Evidence** (validator 6.5.28, `-tx n/a`, pinned packages, 2026-11-11):
  55, 69 and 21 errors. Only 5, 6 and 3 are root errors, all of one kind: a
  **required** binding whose code system is not in the pinned packages and
  cannot be resolved offline:
  - `Patient.communication.language` → `KBV_VS_Base_CommonLanguages` (BCP-47: `de`, `de-DE`, `en`, `fi`, `fr`)
  - `category` → `KBV_VS_MIO_DIGA_Activity_Type`, `_Environmental_Factors`, `_Functional_Assessment_Type` (ICF: `d920`, `e225`, `b730-b749`)
  - `Condition.category` → `KBV_VS_MIO_DIGA_Problem_Type` (SNOMED CT `409586006`)

  Every other error is a cascade: the resource fails its profile, so each
  reference to it reports *Unable to find a profile match*.
- **Consequence**: the kit's golden bundles pass the offline gate because
  they do not use these elements yet. Mappers for Procedure_Activity,
  Functional_Assessment, Environmental_Factor, Condition_Problem or
  `Patient.communication` will hit the same errors. Offline, "0 errors" is
  not reachable for the official examples themselves.
- **Handling (open)**: test two ways to supply the terminology before those
  mappers are built: `-tx https://tx.fhir.org/r4` on 6.5.28, and loading
  gematik's terminology package `gematik.kbv.sfhir.cs.vs` (the one the
  Referenzvalidator `diga` plugin depends on) as an extra `-ig`.
