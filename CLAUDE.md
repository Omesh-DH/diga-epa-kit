# diga-epa-kit

Open-source Python library (Apache-2.0) that turns typical DiGA data into
KBV **MIO DiGA 1.1.0** FHIR R4 document bundles, plus the evidence for a
thesis on how much interoperability effort it saves a small manufacturer.

## Source of truth

- **`spec/packages/` is the only source of truth** for profiles, slices,
  fixed values, bindings and code-system versions. Pinned in
  `spec/packages.lock.json` (sha256), fetched by `scripts/fetch_spec.py`.
  Read the StructureDefinition JSON under `spec/packages/<name>#<version>/package/`
  before writing or changing a mapper. Check `max: "0"` elements too:
  prohibitions are easy to miss.
- Never invent a code, display, system or version. Copy it from a package
  file, or from LOINC or SNOMED for instrument content, and say where it came from.
- If memory, a web page or a pasted note disagrees with `spec/packages/`,
  the package wins. Record the disagreement in `docs/gaps.md`.
- Target version: `spec/VERSION`. Everything version-specific lives in
  `src/diga_epa_kit/terminology/versions.py`.

## The gate

Nothing is committed until the validator reports **zero errors**:

- `make test` runs the unit and golden tests (pytest, no Java).
- `make validate` runs the HL7 FHIR validator **6.5.28** on `tests/golden/*.json`,
  with packages from `spec/packages/` and `-tx n/a`.

Why HL7 and not the gematik Referenzvalidator: its only DiGA plugin
(`diga-0.10.0`) targets 1.0.0-festlegung. Switch once a 1.1.0 plugin exists
(docs/decisions/0001). Why 6.5.28: 6.7+ abort on KBV's snapshot-less
profiles, 6.3 errors on offline bindings (docs/decisions/0004). Warnings are allowed. Known spec-level
findings are listed in `docs/gaps.md`; don't "fix" them by breaking a
profile pattern.

## Commands

Windows has no make here. Each target is one script, run with `.venv/Scripts/python.exe`:

| make | script |
| --- | --- |
| `make setup` | `python -m venv .venv && pip install -e ".[dev]"` + `scripts/fetch_spec.py` |
| `make test` | `pytest -q` |
| `make golden` | `UPDATE_GOLDEN=1 pytest -q tests/golden`, then review the diff |
| `make validate` | `scripts/validate.py --record` |
| `make inventory` | `scripts/spec_inventory.py` (rewrites docs/spec-inventory.md) |

Java: portable Temurin 17 at `%LOCALAPPDATA%\Programs\Temurin\jdk-17.0.20.1+1\bin`
(prepend it to PATH). Python's TLS store fails behind this machine's proxy;
scripts download through curl (`scripts/_net.py`). Never disable TLS checks.

## Layout

- `src/diga_epa_kit/input/`: pydantic input model. No FHIR in it.
- `src/diga_epa_kit/mappers/`: one module per area, one function per resource. Each takes the `VersionPack` explicitly.
- `src/diga_epa_kit/terminology/`: version packs and the PROM instrument catalogue.
- `src/diga_epa_kit/bundle.py`: assembly, with deterministic UUIDv5 ids.
- `src/diga_epa_kit/validation.py`: in-process Bundle invariant checks.
- `synthetic/archetype_*/`: synthetic inputs only. Never real patient data.
- `tests/unit/`, `tests/golden/` (one reviewed bundle per synthetic input), `tests/validator/` (`pytest -m validator`).
- `docs/`: STATUS.md (handoff), spec-inventory.md, gaps.md, decisions/ (ADRs), mapping.md.
- `research/`: timelog.csv, metrics.csv, interviews/, regulatory/.
- `thesis/drafts/`: written only by the thesis-writer agent.

## Working rules

- One phase per session: start from the phase prompt, plan, build with
  `/new-mapper`, loop `/fix-validation` until zero errors, have the
  `fhir-reviewer` agent review, then `/status` and commit.
- Log effort in `research/timelog.csv` (date, hours, activity, area, errors
  before and after). It feeds the cost model, so log honestly, including dead ends.
- Code style: plain dicts out, typed input in, short comments that only say *why*.
- Subagents `regulatory-researcher` and `thesis-writer` write only into
  `research/` and `thesis/`.
- Out of scope: real TI/VAU/HealthID connection, a production ePA client, BfArM
  listing, legal opinions. GeDIG is a draft law, so treat it as such.
