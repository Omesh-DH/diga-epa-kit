# 0009 ePA medication import: read gematik's list, re-export as MIO DiGA

Date: 2026-11-16. Status: accepted (user decisions of the same day).

## Context

Plan phase 6 asks for an import stub: data that comes from the ePA into the
DiGA. Decision 0005 identified the carrier: not MIO DiGA but gematik's
`de.gematik.epa.medication` 1.3.5, the model of the electronic medication
list (eML). Its `$medication-list` operation (OperationDefinition
getMedicationList_MedicationSvc) returns a FHIR searchset Bundle of
MedicationStatement, Medication, MedicationRequest, MedicationDispense,
Provenance and the patient, prescriber and pharmacy involved. The result is
paged (`_count`, `_offset`); gematik's own example is the first page of 16
entries.

## Decisions

1. **Reference package.** `de.gematik.epa.medication` 1.3.5 (Apache-2.0) is
   pinned by sha256 in `spec/packages.lock.json` under `reference_packages`.
   It is fetched like the other packages but not loaded by the validator
   gate, which keeps validating MIO DiGA bundles against the same three
   packages as before. Its dependencies are not fetched. The reader reads no
   package at run time; tests use this one to check the reader against
   gematik's labels and example.
2. **A parser, not a client.** `diga_epa_kit.epa_import.read_medication_list`
   takes a Bundle the DiGA already holds. Fetching it (TI, VAU,
   authentication, the operation call) stays out of scope.
3. **Data minimisation.** The reader looks only at each MedicationStatement
   and the Medication it refers to. The Patient, Practitioner, Organization,
   MedicationRequest, MedicationDispense and Provenance resources in the
   same Bundle are never read, and a test checks that their identifiers and
   names do not appear in the result. Free text that is read, the drug name
   and the dosage text, can still contain a name if someone typed one in; the
   reader does not filter free text. The statement's `subject` is not read
   either, so a list that belongs to another patient is not detected. The
   `import-medication` output keeps the eML statement ids as internal keys;
   they are not exported.
4. **Into the same input model.** The result is a list of the kit's own
   `Medication` input objects (name, PZN, status, dosage text, dates), so a
   medication typed into the app and one read from the ePA are exported the
   same way.
5. **Entries are skipped, never guessed.** An entry marked entered-in-error,
   one whose medication is missing from the Bundle, or one whose medication
   has no name is reported as skipped with the reason. "No name" covers
   ingredient-only and compounded medications and PZN-only entries; the
   export needs a name, also as the display of a PZN coding (gap G18).
   gematik's examples include all three kinds. A malformed PZN, a partial
   date, a dosage text over 1000 characters, or an effectiveDateTime (a point
   in time, which as "since" would read as ongoing) is left out with a note
   and the rest is kept. A Bundle with a `next` link gets a note that it is
   one page of a longer list.
6. **Re-export** (user decision): each medication becomes a
   `KBV_PR_MIO_DIGA_Medication` and a
   `KBV_PR_MIO_DIGA_MedicationStatement_Medication_Information` in the
   section "Medikation".
7. **Information source = the patient** (user decision). The profile
   requires a source and allows only persons. The true source of ePA data is
   the prescriber or pharmacy, by way of the ePA; naming the patient is not
   literally true (docs/gaps.md G17).
8. **PZN version = 1.3.2** (user decision). The profile requires a version
   on a PZN coding and nothing says which (docs/gaps.md G18).
9. **A note on every imported entry.** `note.text` says, in gematik's own
   German labels, where the entry came from and what its status meant in the
   list, for example "Aus der ePA-Medikationsliste übernommen. Herkunft:
   Verschreibung. Status dort: offen." The sentence frame is the kit's own
   wording. It keeps decision 7 and the status (gap G19) from being misread.

## Consequences

- Not carried over: prescription and dispense details, the prescriber, the
  structured dosage (only its one-line text) and ingredients. The eML's
  context (prescription or added entry) survives only as words in the note.
- The eML status values are `unknown`, `entered-in-error` and `intended`.
  gematik labels `unknown` "offen" (open, current), while KBV's German
  concept map translates the same FHIR code as "Unbekannt". Re-exported as
  `unknown`, an open entry can read as "status unknown" (gap G19); the note
  of decision 9 says what was meant.
- The reader handles one page. The DiGA must request and pass in every page
  of the list.
- The reader does not know the export period. An imported medication that
  ended long before the period is still exported, and one that starts after
  the period end makes `build` reject the whole export.
- Only the medication list is read. The medication plan (eMP) and every
  other ePA content are not.
- Not carried over although the eML has them: the drug form (`form`, a KBV
  Darreichungsform coding without version) and ATC codes. The MIO profile
  could take `form.text` and an `atcCode`; left for later.
- Tested with the kit's own synthetic list, with gematik's list example and
  with all 13 MedicationStatement examples in the package (10 imported, 3
  skipped for having no name). Not tested against a real ePA.
