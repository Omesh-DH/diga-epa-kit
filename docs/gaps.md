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
- **Tested, 2026-11-11, both ways of supplying the terminology fail**:
  - *gematik terminology package* `gematik.kbv.sfhir.cs.vs` 1.2.0 (from
    `gematik/app-referencevalidator-plugins`, the one the `diga` plugin
    depends on): ruled out by inspection, no run. It holds 13 small KBV key
    tables and no ICF, BCP-47 or SNOMED content.
  - *Online server* (`-tx https://tx.fhir.org/r4`, validator 6.5.28, one run
    from this machine, behind an HTTPS-intercepting proxy): 115, 161 and 33
    errors on the official bundles, more than offline. The kit's own golden
    bundles, clean offline, report 62. The root errors are transport
    failures, not content: `java.net.SocketTimeoutException: timeout`,
    value-set validation that "took too long to process (>60sec)", and the
    server rejecting the validator's cache id ("was never issued by this
    server"). A required binding that cannot be checked is reported as a
    failed binding, so the result is noise. Not repeated from another
    network, so whether the proxy or the server is at fault is open.
- **Handling (open, needs a decision)**: the offline gate stays as it is.
  Before mappers that use these value sets are built, the gate needs a rule
  for required bindings it cannot resolve; the options are in
  `docs/STATUS.md`.

## G8 A goal or plan made by the DiGA has no valid author

- **Where**: `KBV_PR_MIO_DIGA_Goal` `Goal.expressedBy` and
  `KBV_PR_MIO_DIGA_CarePlan` `CarePlan.author`, both must-support.
- **Evidence**: the allowed targets are Patient, Practitioner, RelatedPerson
  and PractitionerRole. Device_DIGA is not among them.
- **Consequence**: when the DiGA itself proposes a goal or generates an
  exercise plan, which is the usual case, the document cannot say so. The
  only link to the DiGA is the Composition author.
- **Handling**: the kit fills both elements with the patient only when the
  input states it (`set_by_patient`, `written_by_patient`) and leaves them
  out otherwise. It never defaults to the patient.

## G9 Instrument codes cannot be checked against the pinned LOINC version

- **Where**: `terminology/instruments.py`, every `total_score` code. The
  profiles require `code.coding.version` and `display` and pin LOINC 2.72.
- **Evidence**: the pinned packages contain no LOINC content, the offline
  validator only warns that 2.72 "could not be found", and loinc.org refuses
  automated requests (HTTP 403, 2026-11-12). The name of 72514-3 was taken
  from the title of loinc.org/72514-3 as shown in search results, which is
  the current release, not 2.72.
- **Consequence**: a display that changed between 2.72 and today would pass
  the gate unnoticed. The same holds for any code a manufacturer adds.
- **Checked in a browser on loinc.org, 2026-11-12** (the page shows when a
  term was last changed):

  | Code | Long common name today | Last changed | 2.72 name confirmed |
  | --- | --- | --- | --- |
  | 97909-6 | Oswestry disability index score ODI | 2.70 | yes, inferred: unchanged since 2.70 |
  | 44261-6 | Patient Health Questionnaire 9 item (PHQ-9) total score [Reported] | 2.73 (minor) | no |
  | 70274-6 | Generalized anxiety disorder 7 item (GAD-7) total score [Reported.PHQ] | 2.73 (minor) | no |
  | 39156-5 | Body mass index (BMI) [Ratio] | 2.73 (minor) | no |
  | 41950-7 | Number of steps in 24 hour Measured | 2.48 (minor) | yes, inferred: unchanged since 2.48 |
  | 72514-3 | Pain severity - 0-10 verbal numeric rating [Score] - Reported | 2.82 (minor) | no |

- **Handling (open)**: for the four unconfirmed names, compare with the LOINC
  2.72 table (needs a free LOINC account). Until then the kit emits today's
  name with the pinned version.

## G10 The gate can fail on a timeout when the machine is busy

- **Where**: validator 6.5.28, offline, any bundle.
- **Evidence** (2026-11-12): one run reported a single error on an unchanged
  bundle, at `Composition.type`: "The value set
  'http://hl7.org/fhir/ValueSet/doc-typecodes|4.0.1' validation (local) took
  too long to process (>60sec)" (issue code `too-costly`). Other work was
  running on the machine at the time. The rerun, alone, reported 0 errors;
  the same check normally ends as a warning.
- **Consequence**: an error with code `too-costly` says nothing about the
  bundle. In CI on a small runner it would look like a failed gate.
- **Handling**: run the gate with nothing else running and rerun once on a
  `too-costly` error. Since 2026-11-14 the gate reports such findings as
  TIMEOUT, not as bundle errors: the run ends with exit code 4
  (inconclusive) and is not recorded in `research/metrics.csv`.

## G11 A BMI is a vital sign that cannot go into the vital-signs subsection

- **Where**: `Composition.section:befundeUndErgebnisse`, its subsection
  `vitalzeichenUndKoerpermasse`, and `Observation.category`.
- **Evidence**: FHIR R4 requires category `vital-signs` for LOINC 39156-5;
  the validator says "Validate Observation against the Body mass index
  profile (http://hl7.org/fhir/StructureDefinition/bmi) which is required by
  the FHIR specification because the LOINC code 39156-5 was found". The entry
  list of "Vitalzeichen und Körpermaße" is closed and has no profile that
  can carry a BMI; neither `kbv.mio.diga` 1.1.0 nor `kbv.basis` 1.3.0 has a
  BMI profile.
- **Consequence**: the only conformant place is `Observation_Free` as a
  direct entry of "Befunde und Ergebnisse", so a vital sign sits next to,
  not inside, the vital-signs subsection.
- **Also**: `befundeUndErgebnisse.entry` is the only section entry without
  the sub-constraints the other sections have (`entry.reference` min 1;
  `entry.type`, `identifier`, `display` max 0). The kit emits only
  `reference`, so its output is unaffected.
- **Handling**: as above; documented in `docs/mapping.md`. A question for
  support.mio@kbv.de.

## G12 Device.version.type is required but no code is defined for it

- **Where**: `KBV_PR_MIO_DIGA_Device_DIGA`, `Device.version.type` and
  `Device.version.type.coding`.
- **Evidence**: once a version is given, `version.type` is required (min 1)
  and `type.coding` is must-support with system, version, code and display
  each required. Neither Device_DIGA nor `KBV_PR_Base_Device` binds a value
  set, FHIR R4 core has no binding, and no pinned package names a code for
  "software version". The only package file with a filled `Device.version`,
  kbv.basis `examples/device.json`, puts the v2-0203 code `RI` ("Resource
  identifier") there, which does not describe a version. Not checked: how
  the official mio42 example bundles fill the element.
- **Consequence**: a manufacturer cannot fill the must-support coding
  without inventing a code. Receivers cannot tell a software version from
  any other version by code.
- **Handling**: the kit states the kind as text (`type.text` =
  "Softwareversion") and sets no coding (docs/mapping.md). A question for
  support.mio@kbv.de. Also: the Device id does not depend on the version,
  so the same Device id can carry different versions in different exports.

## G13 The packages do not say whether entries must lie inside the period

- **Where**: `Composition.extension:betrachtungszeitraum`
  (`KBV_EX_MIO_DIGA_Betrachtungszeitraum`) and `effective[x]` of every
  section entry.
- **Evidence**: the extension only requires `valuePeriod.start` and `.end`.
  The Composition has one invariant (`date-1`, date precision), the Bundle
  two (`bundle-1`, `bundle-2`: profile prefix, exactly one Composition).
  None ties the date of an entry to the period, and no description says so
  in words.
- **Consequence**: a manufacturer cannot tell from the specification
  whether a value recorded before the period, such as a body height entered
  at the start of use, may be exported.
- **Handling**: the kit's own rule. Dated measurements must lie inside the
  period; a body height, a goal and a plan may be older but not later than
  the period end. A reader can therefore see a vital sign dated before
  `valuePeriod.start`. A question for support.mio@kbv.de.

## G14 Oxygen saturation: a device as the method, and two codings that differ

- **Where**: `KBV_PR_Base_Observation_Peripheral_Oxygen_Saturation` 1.3.0
  (base of the MIO DiGA profile), `Observation.method` and
  `Observation.code.coding`.
- **Evidence**: `method` is required and fixed by pattern to SNOMED
  448703006 "Pulse oximeter (physical object)", which names a device, not a
  method. The LOINC slice is fixed to 2708-6 with display "Oxygen
  saturation in Arterial blood", the SNOMED slice to 431314004 "Peripheral
  oxygen saturation (observable entity)": the two codings of one value name
  different things.
- **Consequence**: a saturation from any other source cannot be expressed
  in this profile, and every export asserts a measurement method the
  manufacturer may never have recorded.
- **Handling**: follow the patterns. The input field accepts pulse-oximeter
  readings only and says so. A question for support.mio@kbv.de.

## G15 Glucose: the method version contradicts its value set; the code pairing is defined only in a concept map

- **Where**: `KBV_PR_MIO_DIGA_Observation_Glucose_Concentration`,
  `Observation.method.coding:codeSnomed` and `Observation.code.coding`;
  kbv.basis `KBV_VS_Base_Glucose_Concentration_Method_SNOMED_CT` and
  `KBV_CM_Base_Terminology_Complete_German`.
- **Evidence, method version**:
  - The MIO profile fixes the SNOMED version of the method coding by
    pattern to `.../version/20220331`. It is the only pattern in the 44 MIO
    DiGA profiles that fixes a SNOMED version without a code; the kbv.basis
    base profile fixes no version there.
  - The value set that coding is bound to (extensible) lists its seven
    concepts under `.../version/20220131`, and so does the concept-map
    group for these codes. Of the 26 SNOMED includes in the kbv.basis 1.3.0
    value sets, 23 state 20220331; this is one of the three that do not.
  - The same seven codes with the same displays are in the 20220331
    expansion of `KBV_VS_Base_Procedure_SNOMED_CT`, so they exist in both
    versions.
  - Checked with the validator (6.5.28, offline) on 2026-11-15: a method
    coding with version 20220131 is an error, "Slice
    'Observation.method.coding:codeSnomed': a matching slice is required,
    but not found". With 20220331 the bundle passes.
- **Evidence, code pairing**:
  - The LOINC value set separates "Blood" from "Body fluid", the SNOMED
    value set "Blood" from "Interstitial fluid". Both codings are required.
  - Which goes with which is stated only indirectly: the concept map
    translates the "Body fluid" LOINC codes and the interstitial-fluid
    concept to the same German concept ("Gewebezuckerkonzentration") and
    the "Blood" codes and the blood concept to the other
    ("Blutzuckerkonzentration"). No invariant enforces the pairing, and
    LOINC "Body fluid" is broader than interstitial fluid.
  - The concept map also narrows the method codes. The "lunch time",
    "supper time" and "bedtime" concepts are translated as *before* lunch,
    supper and going to bed, and "Glucose measurement by monitoring device"
    as continuous glucose monitoring (CGM). The English displays do not say
    that.
- **Consequence**: a coding that follows the value set's own version fails
  the profile. A manufacturer who reads only the profile and the English
  displays can pair the codes differently, or tag an after-lunch value
  with the "lunch time" code, which a German receiver reads as "before
  lunch".
- **Handling**: the kit uses the version the pattern fixes, pairs the codes
  as the concept map does, names its input choices after the German
  meaning, and states CGM for every interstitial reading and for no blood
  reading. Unit tests check all of this against the pinned package files,
  and the validator's negative control covers the version. A question for
  support.mio@kbv.de.
- **Correction (2026-11-15)**: the first version of this entry said the
  pairing was undefined. The fhir-reviewer found the concept map.
