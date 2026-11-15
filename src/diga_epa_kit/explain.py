"""Plain-language explanations for messages of the HL7 FHIR validator.

Only message shapes that were actually seen while building this kit are
listed (validator 6.5.28). An unknown message gets no guess: the caller is
told how to look the element up in the profile instead.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Explanation:
    title: str
    text: str
    about_bundle: bool  # False: the finding says nothing about whether the bundle is correct


_RULES: list[tuple[re.Pattern[str], Explanation]] = [
    (
        re.compile(r"max allowed = 0"),
        Explanation(
            "Element prohibited by the profile",
            "The profile sets this element to max 0, so it must not appear at all. Remove it from the "
            'resource. Prohibitions are easy to miss: look for `"max": "0"` in the profile\'s differential.',
            True,
        ),
    ),
    (
        re.compile(r"minimum required = \d+"),
        Explanation(
            "Required element missing",
            "The profile requires this element (min 1 or more) and the resource does not have it, or has too "
            "few. Add it. If it sits inside a slice, the whole slice with its fixed values is required.",
            True,
        ),
    ),
    (
        re.compile(r"a matching slice is required, but not found"),
        Explanation(
            "Required slice missing or not matched",
            "The profile requires an entry that matches a named slice, and a slice fixes values such as "
            "system, version or code. Either the entry is missing or one of its fixed values differs: "
            "compare it with the slice's pattern in the profile's differential. A coding with another "
            "code-system version than the pattern does not match.",
            True,
        ),
    ),
    (
        re.compile(r"Unable to find a profile match for"),
        Explanation(
            "Follow-on error: a referenced resource fails its profile",
            "A section entry must point to a resource that conforms to one of the listed profiles, and the "
            "referenced resource has an error of its own. Fix the errors reported on that resource (same "
            "urn:uuid) first; this message then disappears.",
            True,
        ),
    ),
    (
        re.compile(r"None of the codings provided are in the value set"),
        Explanation(
            "Code is not in the bound value set",
            "The element is bound to a value set and none of the codings is a member. With a required "
            "binding this is an error: take a code from the value set file in the profile package. With an "
            "extensible or preferred binding it is a warning and may be acceptable.",
            True,
        ),
    ),
    (
        re.compile(r"took too long to process"),
        Explanation(
            "Validator timeout",
            "The validator gave up on a slow check (issue code too-costly). This happens when the machine "
            "is busy. Rerun the validation with nothing else running (docs/gaps.md G10).",
            False,
        ),
    ),
    (
        re.compile(r"could not be found, so the code cannot be validated"),
        Explanation(
            "Code system version not available offline",
            "The validator has no copy of this code system version (LOINC, SNOMED CT), so it cannot check "
            "the code or its display. Expected when running without a terminology server; the code itself "
            "must be checked against the terminology by other means (docs/gaps.md G9).",
            False,
        ),
    ),
    (
        re.compile(r"running without terminology services|Unable to validate code without using server"),
        Explanation(
            "Code not checked: no terminology server",
            "The run uses no terminology server (-tx n/a), so this code was not checked. It is neither "
            "confirmed nor rejected.",
            False,
        ),
    ),
    (
        re.compile(r"Unable to check whether the code is in the value set"),
        Explanation(
            "Value-set membership not checked",
            "The value set draws on a code system the validator does not have offline, so membership could "
            "not be checked. Compare the code with the value set file in the package by hand.",
            False,
        ),
    ),
    (
        re.compile(r"dom-6"),
        Explanation(
            "No narrative (best practice)",
            "FHIR recommends a human-readable text for every resource. The MIO DiGA profiles do not require "
            "it; this is a recommendation, not a profile violation.",
            False,
        ),
    ),
    (
        re.compile(r"UCUM Codes that contain human readable annotations"),
        Explanation(
            "UCUM annotation in a unit",
            "Units such as {score} carry meaning only in the braces, which UCUM ignores when comparing "
            "units. This is a best-practice warning; the profile allows the unit.",
            False,
        ),
    ),
]

_UNKNOWN = Explanation(
    "No explanation on file",
    "This message is not one the kit knows. Take the element path at the start of the message, open the "
    "profile named in meta.profile under spec/packages/, and read that element's rules in the differential "
    "(min, max, fixed and pattern values, binding). Then check the base profiles it names.",
    True,
)


def explain(message: str) -> Explanation:
    for pattern, explanation in _RULES:
        if pattern.search(message):
            return explanation
    return _UNKNOWN


def is_known(message: str) -> bool:
    return explain(message) is not _UNKNOWN
