"""Reading data from the ePA into the kit's input model (import direction).

A stub: it parses FHIR the DiGA has already received. Fetching it (TI, VAU,
authentication, the getMedicationList operation itself) is out of scope.
"""

from .medication_list import Finding, ImportResult, read_medication_list

__all__ = ["Finding", "ImportResult", "read_medication_list"]
