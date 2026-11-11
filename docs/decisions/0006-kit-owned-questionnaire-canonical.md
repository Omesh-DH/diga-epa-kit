# 0006 Kit-owned Questionnaire canonical

Date: 2026-11-11. Status: superseded by 0007 the same day (PROMs are exported as scores only, so the kit emits no Questionnaire).

## Context

The PHQ-9 `Questionnaire` used `http://loinc.org/q/44249-1` as `url`. That
canonical belongs to LOINC's published form, whose linkIds and structure
differ from the kit's rendition (`q1`..`q9`). A receiver resolving the
canonical externally would get a form that does not match the
`QuestionnaireResponse.item.linkId` values (fhir-reviewer finding 2,
2026-11-02).

`KBV_PR_MIO_DIGA_Questionnaire|1.1.0` leaves `url` (0..1, must-support) and
`version` unconstrained. `QuestionnaireResponse.questionnaire` is a required
canonical.

## Decision

- `Questionnaire.url` = `<KIT_CANONICAL_BASE>/Questionnaire/<instrument key>`.
- `Questionnaire.version` = the rendition version on the `Instrument`
  (`1.0.0`). Bump it whenever linkIds, item order or texts change.
- `QuestionnaireResponse.questionnaire` = `url|version`, so a response always
  names the exact rendition it answers.
- LOINC still identifies the instrument, through `Questionnaire.code` (panel)
  and `item.code`.

## Open

`KIT_CANONICAL_BASE` in `terminology/instruments.py` is
`https://diga-epa-kit.example/fhir`. `.example` is reserved (RFC 2606) and
resolves nowhere. Replace it with a URL the project controls (for example the
repository's pages URL) before any real export. Changing it changes the
Questionnaire resource id and the golden bundles.
