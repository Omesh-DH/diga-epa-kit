# 0003 Plain dicts out, typed input in

Date: 2026-11-02. Status: accepted.

`fhir.resources` and similar models know base R4 only, not KBV slices,
patterns or prohibitions, so they add a dependency without catching profile
errors. Mappers emit JSON dicts. The pydantic input model (`input/model.py`)
rejects bad source data early. The validator is the source of truth for FHIR
conformance, and `validation.py` is the cheap in-process first line.
