---
description: Write the session handoff to docs/STATUS.md and prepare the commit
---

Close the session.

1. Run `pytest -q` and `scripts/validate.py --record`. If either fails,
   stop: nothing is committed until the gate reports zero errors.
2. Rewrite `docs/STATUS.md`:
   - **Phase**: current phase and its exit check, met or not.
   - **Gate**: last validator result (version, tx mode, errors and warnings),
     copied from `research/metrics.csv`.
   - **Done this session**: mappers, tests, docs.
   - **Open**: next mapper or step, blocking questions, and new entries in `docs/gaps.md`.
   - **Effort**: hours logged this session from `research/timelog.csv`.
3. Run `scripts/spec_inventory.py` if mappers changed.
4. Show `git status` and `git diff --stat`, propose a commit message
   (imperative, scope first, e.g. `mappers: add heart rate`), and commit
   only after the user confirms.
