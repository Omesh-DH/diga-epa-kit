# 0004 Pin HL7 FHIR validator 6.5.28

Date: 2026-11-02. Status: accepted.

## Context

KBV ships `kbv.mio.diga#1.1.0` without snapshots (gaps G4), so the validator
generates them, and the outcome depends on its release. Bisection, both golden
bundles, `-tx n/a`, packages from `spec/packages/`:

| Validator | A, PHQ-9 | B, weight |
| --- | --- | --- |
| 6.3.14 | 0 errors (111 warnings) | **25 errors**: required LOINC 2.72/UCUM bindings unresolvable offline (G5) |
| **6.5.28** | **0 errors (118 warnings)** | **0 errors (76 warnings)** |
| 6.7.11 | **crash**: *Slice encountered midway through set*, Functional_Assessment | 0 errors (45 warnings) |
| 6.9.12 | crash (same) | 0 errors (45 warnings) |
| 6.10.4 | crash (same) | 0 errors (45 warnings) |

## Decision

Pin 6.5.28, the only tested release that validates both archetypes without
crashing or failing offline bindings. A negative control
(`tests/validator/test_validator.py`) puts two known violations into a copy
of a golden bundle, a prohibited `referenceRange.text` and a missing
`Device.identifier`. It asserts the validator reports both, so the gate can't
pass by checking nothing.

## Consequences

- `/spec-check` re-tests newer releases, and the pin moves only when a newer one
  passes both golden bundles and the negative control.
- Thesis evidence (sub-question 2): for the same bundle, "valid" flips between
  validator releases. A manufacturer has to pin and re-qualify the tool, which
  is a recurring cost the effort model should include.
