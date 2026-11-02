---
description: Re-verify the pinned spec and tooling against the live registries
---

Check whether anything the project depends on has moved. Report, don't change code.

1. `scripts/fetch_spec.py`: do the pinned packages still match their sha256?
2. Simplifier feed `https://packages.simplifier.net/kbv.mio.diga`: is there
   a version newer than `spec/VERSION`? Also check kbv.basis and de.basisprofil.r4.
3. gematik `app-referencevalidator-plugins` releases: is there a `diga-*`
   plugin newer than `diga-0.10.0`, and which `kbv.mio.diga` version does its
   `valmodule-diga/src/main/resources/plugin/config.yaml` target? If it
   targets `spec/VERSION`, flag that the gate can switch to the Referenzvalidator.
4. `de.gematik.epa.medication`: latest version (input for `epa_import/`).
5. HL7 validator releases: is there a version newer than the pinned one that
   validates `tests/golden/` without crashing? Test it with
   `scripts/validate.py --validator-version X`.
6. `scripts/spec_inventory.py`: refresh `docs/spec-inventory.md`.

Write findings as a dated entry in `docs/decisions/` if anything changed,
otherwise one line in `docs/STATUS.md`.
