---
description: Add a mapper for one MIO DiGA profile, from spec to golden bundle
argument-hint: <profile name, e.g. Observation_Heart_Rate> [archetype]
---

Add a mapper for **$ARGUMENTS**.

1. **Read the spec.** Open the StructureDefinition in
   `spec/packages/kbv.mio.diga#1.1.0/package/` and its `baseDefinition` chain
   (kbv.basis, de.basisprofil.r4). List every element with `min >= 1`, every
   `fixed*`/`pattern*`, every required binding and its ValueSet contents, and
   every `max: "0"`. Note the Composition section slice that lists this
   profile as an allowed `entry` target.
2. **Input model.** Add the smallest typed input to `input/model.py`, with
   no FHIR concepts. Validate units, ranges and timezone-aware datetimes there.
3. **Version pack.** Add the profile key in `terminology/versions.py`.
4. **Mapper.** One function in the right `mappers/` module. Use `meta()`,
   `ri_identifier()` and `loinc()` from `mappers/common.py`. Copy codes,
   displays and versions from the package and cite the source file in your summary.
5. **Bundle and Composition.** Wire the mapper into `bundle.py` and the
   correct section in `mappers/composition.py`, in profile slice order.
6. **Synthetic data.** Extend or add a file in `synthetic/archetype_*/`.
7. **Tests.** Add unit tests in `tests/unit/` for shape, references, and
   rejection of bad input. Regenerate golden files with
   `UPDATE_GOLDEN=1 pytest tests/golden` and read the diff.
8. **Gate.** Run `scripts/validate.py`. If there are errors, use `/fix-validation`.
9. Update `docs/mapping.md` and add a `research/timelog.csv` row.

Stop and ask if the profile needs a decision the spec doesn't settle (for
example, which of two allowed target profiles to use).
