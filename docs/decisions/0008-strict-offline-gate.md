# 0008 Gate stays strict; profiles with unresolvable bindings wait

Date: 2026-11-11. Status: accepted (user decision).

## Context

Four value sets with a required binding cannot be resolved by the offline
gate, and neither tested terminology source fixes that (gaps G7). KBV's own
example bundles fail on them.

## Decision

The gate keeps its plain meaning: zero errors from the HL7 validator
6.5.28, offline, no tolerated errors. Profiles and elements that need those
value sets are not built for now:

| Blocked | Element | Value set |
| --- | --- | --- |
| Procedure_Activity | `category` | KBV_VS_MIO_DIGA_Activity_Type (ICF) |
| Observation_Functional_Assessment | `category` | KBV_VS_MIO_DIGA_Functional_Assessment_Type (ICF) |
| Observation_Environmental_Factor | `category` | KBV_VS_MIO_DIGA_Environmental_Factors (ICF) |
| Condition_Problem | `category` | KBV_VS_MIO_DIGA_Problem_Type (SNOMED CT) |
| Patient | `communication.language` (optional element) | KBV_VS_Base_CommonLanguages (BCP-47) |

## Consequences

- Phase 3 order: vital signs, Diary_Entry, Observation_Free, Goal, CarePlan,
  DocumentReference and Provenance first.
- Archetype C's functional score goes out as Score_or_Assessment_by_Scale,
  not Functional_Assessment. Archetype D's exercise sessions (Procedure_Activity)
  are blocked; its CarePlan and adherence diary are not.
- Revisit when a mapper for a blocked profile is the next one due. The
  alternatives then are a named allow-list with in-process code checks, or
  an online run from a network without the proxy.
- The blocked profiles are a finding for the thesis: an SME cannot validate
  them with freely available offline tooling.
