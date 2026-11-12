# Licensing

Taken from section 9 of the agreed project plan (2026-10-25), with the state
of this repo added. This is a careful reading of published terms, not legal
advice. The university's legal office or the supervisor should sign off
before the open-source release.

| Component | Terms | Status | Rule for this repo | State |
| --- | --- | --- | --- | --- |
| HL7 FHIR R4 core | CC0; "FHIR" and the flame are HL7 trademarks | OK | No "FHIR" in project or package name; trademark line in README | Name is `diga-epa-kit`. Trademark line: TODO |
| KBV MIO DiGA package (`kbv.mio.diga`), kbv.basis | No explicit licence found | Unclear for redistribution | Never commit `spec/packages/`; fetch at setup. Ask support.mio@kbv.de and cite the answer | Gitignored, fetched by `scripts/fetch_spec.py`. Email to KBV: TODO (user) |
| de.basisprofil.r4 | HL7 Deutschland terms | Not committed | Same as above | Gitignored |
| SNOMED CT | Licence required; free in Germany via BfArM affiliate licence | Action needed | No SNOMED tables; only codes the profiles fix or bind, with the notice. README states users outside Germany need their own licence | Codes listed below. Affiliate licence: TODO (user). Notice text: TODO |
| LOINC | Free with notice; some scale content has third-party copyright | OK with notice | LOINC notice in NOTICE; check `EXTERNAL_COPYRIGHT_NOTICE` per panel | Notice in THIRD_PARTY.md; official text in NOTICE: TODO. PHQ-9 panel check: TODO |
| UCUM | Free with conditions | OK with notice | Plain UCUM codes; notice | Codes `kg`, `mm[Hg]`, `{score}`. Notice: TODO |
| PHQ-9, GAD-7 | Released by Pfizer without restriction or fee | OK | Cite the authors | PHQ-9 total score only |
| 0–10 numeric pain rating | Generic scale, no instrument licence | OK | Score and LOINC code only, no anchor texts | In use (LOINC 72514-3) |
| Oswestry Disability Index | © Jeremy Fairbank, 1980, all rights reserved (LOINC 97909-6 notice); the notice links to Mapi Research Trust (eprovide.mapi-trust.org) for the instrument; licence terms not checked | Avoid item text | Score and LOINC code only. A manufacturer needs its own licence to administer the questionnaire | Score only (decision 0007) |
| Tinnitus Handicap Inventory | Copyrighted | Avoid item text | Total score only, or a free 0–10 numeric rating scale | Not used |
| Other PROMs | Varies | Check each | Scores and codes only, no item wording | None used |
| gematik Referenzvalidator | Apache-2.0 | OK | Separate process; keep LICENSE/NOTICE if redistributed | Not used as the gate (decision 0001) |
| gematik `diga` plugin | Not confirmed | Verify | Read LICENSE before use; download, don't vendor | Not used |
| mio42 `Validierungspaket-MIO-DiGA-Toolkit` | No licence on the repo (GitHub API, 2026-11-11) | Unclear | Download at test time only; never commit | Used only as downloaded test input |
| HL7 FHIR validator (`validator_cli.jar`) | Apache-2.0 | OK | Downloaded into `.cache/`, never committed | In use (decision 0004) |
| pydantic, pytest | MIT | OK | `pip-licenses` gate in CI | Gate: TODO |

The plan's stack also names `fhir.resources`, Typer, ruff, mypy, mkdocs and
hypothesis. They are not dependencies at present (decision 0003).

## SNOMED CT codes in `src/`

Every code is fixed by a profile pattern or comes from a required value set
in the pinned packages.

| Code | Where | Required by |
| --- | --- | --- |
| 706689003 | `mappers/core.py` | `KBV_PR_MIO_DIGA_DeviceDefinition_DIGA` `type.coding` pattern |
| 27113001 | `mappers/vitals.py` | kbv.basis `KBV_VS_Base_Body_Weight_SNOMED_CT` (required) |
| 363808001, 786458005 | `mappers/vitals.py` | kbv.basis `KBV_VS_Base_Body_Weight_Method_SNOMED_CT` (required) |
| 75367002, 271649006, 271650006 | `mappers/vitals.py` | kbv.basis `KBV_PR_Base_Observation_Blood_Pressure` `codeSnomed` patterns |
| 423100009, 1184593002, 424836000 | `mappers/composition.py` | `KBV_PR_MIO_DIGA_Composition` section code patterns |

## PROM wording

Rule: no questionnaire item wording in code, tests or data; scores and codes
only (decision 0007). The kit exports total scores, and
`tests/unit/test_no_prom_wording.py` fails if a fragment from
`docs/licensing/blocked-phrases.txt` appears in `src/`, `tests/` or
`synthetic/`. Add fragments to that file for every new instrument.
