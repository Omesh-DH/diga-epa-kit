---
description: Drive the validator to zero errors without breaking the spec
argument-hint: [bundle.json ...] (default: tests/golden)
---

Run the gate and fix what it reports: `scripts/validate.py $ARGUMENTS`.

For each error, in order:

1. **Classify it** before touching code:
   - *Mapping bug*: our output violates the profile (wrong cardinality, a
     max=0 element, a wrong pattern, a missing required element). Fix the mapper.
   - *Input gap*: the input model can't express what the profile needs. Extend the input model.
   - *Spec-level*: the profile itself conflicts with terminology or another
     profile, for example a fixed display that LOINC rejects. **Don't work around
     it by breaking the profile.** Add or update an entry in `docs/gaps.md`
     with the exact validator message, profile, element and validator version.
   - *Tooling*: a validator crash or snapshot failure. Record it in
     `docs/decisions/0004-validator-pin.md` and retry on the pinned version.
2. **Find the rule** in `spec/packages/`. Quote the element id and the
   constraint you are satisfying.
3. **Fix it, add a unit test** that would have caught it, and regenerate
   the golden files.
4. **Re-run** until `0 error(s)`.

When clean, run `scripts/validate.py --record` once so the result lands in
`research/metrics.csv`. Log the number of errors before and after, and the
time spent, in `research/timelog.csv`.
