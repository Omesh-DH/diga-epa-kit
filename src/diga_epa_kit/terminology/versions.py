"""Version packs: everything that changes between MIO DiGA releases lives here.

KBV renamed most profiles between 1.0.0-festlegung and 1.1.0 (the ``_Free``
suffixes were dropped) and moved terminology versions, so builders never
hard-code a canonical URL. They ask the active pack instead.
"""

from __future__ import annotations

from dataclasses import dataclass, field

KBV_SD = "https://fhir.kbv.de/StructureDefinition/"

LOINC = "http://loinc.org"
SNOMED = "http://snomed.info/sct"
UCUM = "http://unitsofmeasure.org"
V2_0203 = "http://terminology.hl7.org/CodeSystem/v2-0203"
OBS_CATEGORY = "http://terminology.hl7.org/CodeSystem/observation-category"
PZN = "http://fhir.de/CodeSystem/ifa/pzn"
RFC3986 = "urn:ietf:rfc:3986"


@dataclass(frozen=True)
class VersionPack:
    version: str
    fhir_package: str
    loinc_version: str
    snomed_version: str
    v2_0203_version: str
    # Version of KBV_CS_MIO_DIGA_Section_Codes in the package; not tied to the package version.
    section_codes_version: str
    profiles: dict[str, str] = field(default_factory=dict)

    def profile(self, key: str) -> str:
        """Versioned canonical, as the Bundle invariants and meta.profile slices expect."""
        try:
            name = self.profiles[key]
        except KeyError:
            raise KeyError(f"profile {key!r} is not mapped for MIO DiGA {self.version}") from None
        return f"{KBV_SD}{name}|{self.version}"


MIO_DIGA_1_1_0 = VersionPack(
    version="1.1.0",
    fhir_package="kbv.mio.diga#1.1.0",
    loinc_version="2.72",
    snomed_version="http://snomed.info/sct/900000000000207008/version/20220331",
    v2_0203_version="2.9",
    section_codes_version="1.1.0",
    profiles={
        "bundle": "KBV_PR_MIO_DIGA_Bundle",
        "composition": "KBV_PR_MIO_DIGA_Composition",
        "patient": "KBV_PR_MIO_DIGA_Patient",
        "device_diga": "KBV_PR_MIO_DIGA_Device_DIGA",
        "device_definition_diga": "KBV_PR_MIO_DIGA_DeviceDefinition_DIGA",
        "organization_manufacturer": "KBV_PR_MIO_DIGA_Organization_Manufacturer",
        "body_weight": "KBV_PR_MIO_DIGA_Observation_Body_Weight",
        "blood_pressure": "KBV_PR_MIO_DIGA_Observation_Blood_Pressure",
        "diary_entry": "KBV_PR_MIO_DIGA_Observation_Diary_Entry",
        "observation_free": "KBV_PR_MIO_DIGA_Observation_Free",
        "goal": "KBV_PR_MIO_DIGA_Goal",
        "care_plan": "KBV_PR_MIO_DIGA_CarePlan",
        "score": "KBV_PR_MIO_DIGA_Observation_Score_or_Assessment_by_Scale",
    },
)

PACKS: dict[str, VersionPack] = {p.version: p for p in (MIO_DIGA_1_1_0,)}
DEFAULT_VERSION = MIO_DIGA_1_1_0.version


def get_pack(version: str = DEFAULT_VERSION) -> VersionPack:
    try:
        return PACKS[version]
    except KeyError:
        supported = ", ".join(sorted(PACKS))
        raise ValueError(f"MIO DiGA {version} is not supported (have: {supported})") from None
