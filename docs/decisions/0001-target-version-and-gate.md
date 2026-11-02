# 0001 Target MIO DiGA 1.1.0; gate on the HL7 validator

Date: 2026-11-02. Status: accepted.

## Context

The gematik Referenzvalidator DiGA plugin (`diga-0.10.0`, 2023-12-21, config in
`gematik/app-referencevalidator-plugins/valmodule-diga`) validates against
**kbv.mio.diga 1.0.0-festlegung**. The current KBV package is **1.1.0**
(kbv.basis 1.3.0, de.basisprofil.r4 1.3.2). The two are not compatible:

- Profiles were renamed (1.0.0 `_Free` suffixes dropped, e.g.
  `KBV_PR_MIO_DIGA_Goal_Free` became `KBV_PR_MIO_DIGA_Goal`;
  `Observation_Score_or_Assessment_by_Scale` replaces two assessment profiles).
- `meta.profile` must carry the version (`|1.1.0`), and `bundle-1` rejects any
  entry outside the MIO DiGA family.
- Terminology versions moved (LOINC 2.71 to 2.72 in Composition.type).
- `Device_DIGA.identifier.type.text = DiGA-VE-ID` became mandatory.

A bundle can pass the gematik plugin or the 1.1.0 profiles, not both.

## Decision

Target 1.1.0, the version that is `latest` on the registry. Gate on the HL7 FHIR
validator with the pinned packages in `spec/packages/`. Keep everything
version-specific in `terminology/versions.py`, so a 1.0.0 pack (and a
non-blocking Referenzvalidator run) can be added for the thesis comparison.

## Consequences

Sub-question 3 ("passes the gematik Referenzvalidator") can't be answered
literally for 1.1.0 until gematik ships a matching plugin. `/spec-check` watches
for it. Open: which version is legally binding for ePA export. Cite the source
in the thesis.
