# Third-party material

The kit **uses but does not redistribute** the following. They are fetched at
build time (`scripts/fetch_spec.py`, `scripts/validate.py`) and are excluded
from git.

| Material | Source | Terms |
| --- | --- | --- |
| kbv.mio.diga 1.1.0, kbv.basis 1.3.0 | Kassenärztliche Bundesvereinigung (KBV), packages.simplifier.net | KBV terms of use for MIO specifications; check before redistributing |
| de.basisprofil.r4 1.3.2 | HL7 Deutschland, packages.simplifier.net | HL7 Deutschland terms |
| HL7 FHIR validator (validator_cli.jar) | github.com/hapifhir/org.hl7.fhir.core | Apache-2.0 |
| LOINC codes and displays (in `terminology/instruments.py`, golden bundles) | Regenstrief Institute | LOINC licence: "This material contains content from LOINC (http://loinc.org). LOINC is copyright © Regenstrief Institute, Inc. and the LOINC Committee and is available at no cost under the license at http://loinc.org/license." |
| SNOMED CT codes (fixed by the KBV profiles) | SNOMED International | Use in Germany via the national release centre (BfArM); affiliate licence terms apply |
| PHQ-9 | Pfizer Inc. | Free to use; no permission required. The kit carries only LOINC codes and displays, not the instrument wording |

Python dependency: pydantic (MIT). Dev: pytest (MIT).
