"""Vital signs and body measurements (section Befunde und Ergebnisse > Vitalzeichen)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from ..input.model import BloodPressure, BodyHeight, BodyWeight, Glucose
from ..terminology.versions import LOINC, OBS_CATEGORY, SNOMED, UCUM, VersionPack
from .common import Json, meta, ri_identifier, urn

_WEIGHT_METHOD = {
    "measured": ("363808001", "Measured body weight (observable entity)"),
    "self_reported": ("786458005", "Self reported usual body weight (observable entity)"),
}


def body_weight(pack: VersionPack, uuid: str, patient_uuid: str, obs: BodyWeight, now: datetime) -> Json:
    method_code, method_display = _WEIGHT_METHOD[obs.method]
    return {
        "resourceType": "Observation",
        "id": uuid,
        "meta": meta(pack, "body_weight", now),
        "identifier": [ri_identifier(pack, uuid)],
        "status": "final",
        "category": [{"coding": [{"system": OBS_CATEGORY, "code": "vital-signs"}]}],
        "code": {
            "coding": [
                {"system": LOINC, "version": pack.loinc_version, "code": "29463-7", "display": "Body weight"},
                {
                    "system": SNOMED,
                    "version": pack.snomed_version,
                    "code": "27113001",
                    "display": "Body weight (observable entity)",
                },
            ]
        },
        "subject": {"reference": urn(patient_uuid)},
        "effectiveDateTime": obs.measured_at.isoformat(),
        # Home measurements: the patient is the performer, whether scale-synced or typed in.
        "performer": [{"reference": urn(patient_uuid)}],
        "valueQuantity": {"value": round(obs.kg, 2), "unit": "kg", "system": UCUM, "code": "kg"},
        "method": {
            "coding": [
                {"system": SNOMED, "version": pack.snomed_version, "code": method_code, "display": method_display}
            ]
        },
    }


def body_height(pack: VersionPack, uuid: str, patient_uuid: str, obs: BodyHeight, now: datetime) -> Json:
    return {
        "resourceType": "Observation",
        "id": uuid,
        "meta": meta(pack, "body_height", now),
        "identifier": [ri_identifier(pack, uuid)],
        "status": "final",
        "category": [{"coding": [{"system": OBS_CATEGORY, "code": "vital-signs"}]}],
        "code": {
            "coding": [
                # de.basisprofil.r4 ValueSet VitalSignDE_Body_Height_Loinc.
                {"system": LOINC, "version": pack.loinc_version, "code": "8302-2", "display": "Body height"},
                # kbv.basis KBV_VS_Base_Body_Height_SNOMED_CT: the general concept, because the
                # input does not say whether the patient stood or lay down.
                {
                    "system": SNOMED,
                    "version": pack.snomed_version,
                    "code": "1153637007",
                    "display": "Body height (observable entity)",
                },
            ]
        },
        "subject": {"reference": urn(patient_uuid)},
        "effectiveDateTime": obs.measured_at.isoformat(),
        # Entered or measured at home: the patient is the performer.
        "performer": [{"reference": urn(patient_uuid)}],
        # Unit and code "cm" are the kbv.basis pattern.
        "valueQuantity": {"value": round(obs.cm, 1), "unit": "cm", "system": UCUM, "code": "cm"},
    }


def _bp_component(pack: VersionPack, loinc: tuple[str, str], snomed: tuple[str, str], value: int) -> Json:
    return {
        "code": {
            "coding": [
                {"system": LOINC, "version": pack.loinc_version, "code": loinc[0], "display": loinc[1]},
                {"system": SNOMED, "version": pack.snomed_version, "code": snomed[0], "display": snomed[1]},
            ]
        },
        # Unit text "mm Hg" is the kbv.basis pattern; the UCUM code is mm[Hg].
        "valueQuantity": {"value": value, "unit": "mm Hg", "system": UCUM, "code": "mm[Hg]"},
    }


def blood_pressure(pack: VersionPack, uuid: str, patient_uuid: str, obs: BloodPressure, now: datetime) -> Json:
    # Codes and displays: de.basisprofil.r4 VitalSignDE_Blutdruck (LOINC codes) and
    # kbv.basis KBV_PR_Base_Observation_Blood_Pressure (LOINC displays, SNOMED codings).
    return {
        "resourceType": "Observation",
        "id": uuid,
        "meta": meta(pack, "blood_pressure", now),
        "identifier": [ri_identifier(pack, uuid)],
        "status": "final",
        "category": [{"coding": [{"system": OBS_CATEGORY, "code": "vital-signs"}]}],
        "code": {
            "coding": [
                {
                    "system": LOINC,
                    "version": pack.loinc_version,
                    "code": "85354-9",
                    "display": "Blood pressure panel with all children optional",
                },
                {
                    "system": SNOMED,
                    "version": pack.snomed_version,
                    "code": "75367002",
                    "display": "Blood pressure (observable entity)",
                },
            ]
        },
        "subject": {"reference": urn(patient_uuid)},
        "effectiveDateTime": obs.measured_at.isoformat(),
        # Home measurements: the patient is the performer, whether cuff-synced or typed in.
        "performer": [{"reference": urn(patient_uuid)}],
        # No Observation.value: the base profile prohibits it, the reading lives in the components.
        "component": [
            _bp_component(
                pack,
                ("8480-6", "Systolic blood pressure"),
                ("271649006", "Systolic blood pressure (observable entity)"),
                obs.systolic,
            ),
            _bp_component(
                pack,
                ("8462-4", "Diastolic blood pressure"),
                ("271650006", "Diastolic blood pressure (observable entity)"),
                obs.diastolic,
            ),
        ],
    }


@dataclass(frozen=True)
class _Vital:
    loinc: tuple[str, str]
    snomed: tuple[str, str]
    unit: str
    ucum: str
    method: tuple[str, str] | None = None


# One entry per profile key. LOINC code: pattern in the de.basisprofil.r4 VitalSignDE profile;
# LOINC display and unit text: patterns in the kbv.basis profile; UCUM code: de.basisprofil.r4
# pattern; SNOMED: the kbv.basis value set or pattern. Where a value set offers several
# concepts the general one is used, because the input does not say how or where the value
# was taken.
_SIMPLE_VITALS = {
    "heart_rate": _Vital(
        ("8867-4", "Heart rate"), ("364075005", "Heart rate (observable entity)"), "per minute", "/min"
    ),
    "body_temperature": _Vital(
        ("8310-5", "Body temperature"), ("386725007", "Body temperature (observable entity)"), "Celsius", "Cel"
    ),
    "oxygen_saturation": _Vital(
        ("2708-6", "Oxygen saturation in Arterial blood"),
        ("431314004", "Peripheral oxygen saturation (observable entity)"),
        "%",
        "%",
        # Required and fixed by kbv.basis: this profile only fits pulse-oximeter readings.
        method=("448703006", "Pulse oximeter (physical object)"),
    ),
    "respiratory_rate": _Vital(
        ("9279-1", "Respiratory rate"), ("86290005", "Respiratory rate (observable entity)"), "per minute", "/min"
    ),
}


def simple_vital(
    pack: VersionPack, kind: str, uuid: str, patient_uuid: str, measured_at: datetime, value: float, now: datetime
) -> Json:
    """Heart rate, body temperature, oxygen saturation or respiratory rate: one value, one unit."""
    spec = _SIMPLE_VITALS[kind]
    res: Json = {
        "resourceType": "Observation",
        "id": uuid,
        "meta": meta(pack, kind, now),
        "identifier": [ri_identifier(pack, uuid)],
        "status": "final",
        "category": [{"coding": [{"system": OBS_CATEGORY, "code": "vital-signs"}]}],
        "code": {
            "coding": [
                {"system": LOINC, "version": pack.loinc_version, "code": spec.loinc[0], "display": spec.loinc[1]},
                {"system": SNOMED, "version": pack.snomed_version, "code": spec.snomed[0], "display": spec.snomed[1]},
            ]
        },
        "subject": {"reference": urn(patient_uuid)},
        "effectiveDateTime": measured_at.isoformat(),
        # Home measurements: the patient is the performer, whether device-synced or typed in.
        "performer": [{"reference": urn(patient_uuid)}],
        "valueQuantity": {"value": value, "unit": spec.unit, "system": UCUM, "code": spec.ucum},
    }
    if spec.method:
        res["method"] = {
            "coding": [
                {"system": SNOMED, "version": pack.snomed_version, "code": spec.method[0], "display": spec.method[1]}
            ]
        }
    return res


# kbv.basis KBV_VS_Base_Glucose_Concentration_LOINC (required): the code depends on the
# specimen and on whether the unit is a mass or a molar concentration. Which LOINC code goes
# with which SNOMED code follows kbv.basis KBV_CM_Base_Terminology_Complete_German: it maps
# the "Body fluid" codes and the interstitial-fluid concept to one German concept (tissue
# glucose) and the "Blood" codes and the blood concept to the other (docs/gaps.md G15).
_GLUCOSE_LOINC = {
    ("blood", "mg/dL"): ("2339-0", "Glucose [Mass/volume] in Blood"),
    ("blood", "mmol/L"): ("15074-8", "Glucose [Moles/volume] in Blood"),
    ("interstitial_fluid", "mg/dL"): ("2344-0", "Glucose [Mass/volume] in Body fluid"),
    ("interstitial_fluid", "mmol/L"): ("14745-4", "Glucose [Moles/volume] in Body fluid"),
}
# kbv.basis KBV_VS_Base_Glucose_Concentration_SNOMED_CT (required).
_GLUCOSE_SNOMED = {
    "blood": ("434912009", "Blood glucose concentration (observable entity)"),
    "interstitial_fluid": ("434910001", "Interstitial fluid glucose concentration (observable entity)"),
}
# kbv.basis KBV_VS_Base_Glucose_Concentration_Method_SNOMED_CT (extensible). The input names
# follow the German meaning the same concept map gives each code: the lunch, supper and
# bedtime concepts mean "before".
_GLUCOSE_METHOD = {
    "fasting": ("271062006", "Fasting blood glucose measurement (procedure)"),
    "before_lunch": ("271063001", "Lunch time blood sugar measurement (procedure)"),
    "before_supper": ("271064007", "Supper time blood sugar measurement (procedure)"),
    "before_bed": ("271065008", "Bedtime blood sugar measurement (procedure)"),
    "after_meal": ("302788006", "Post-prandial blood glucose measurement (procedure)"),
    "random": ("271061004", "Random blood glucose measurement (procedure)"),
}
# Same value set. The concept map reads this code as continuous glucose monitoring (CGM),
# which is how interstitial fluid is measured, so it is stated for every sensor reading.
_GLUCOSE_CGM = ("359776002", "Glucose measurement by monitoring device (procedure)")


def glucose(pack: VersionPack, uuid: str, patient_uuid: str, obs: Glucose, now: datetime) -> Json:
    loinc = _GLUCOSE_LOINC[(obs.specimen, obs.unit)]
    snomed = _GLUCOSE_SNOMED[obs.specimen]
    res: Json = {
        "resourceType": "Observation",
        "id": uuid,
        "meta": meta(pack, "glucose", now),
        "identifier": [ri_identifier(pack, uuid)],
        "status": "final",
        "category": [{"coding": [{"system": OBS_CATEGORY, "code": "vital-signs"}]}],
        "code": {
            "coding": [
                {"system": LOINC, "version": pack.loinc_version, "code": loinc[0], "display": loinc[1]},
                {"system": SNOMED, "version": pack.snomed_version, "code": snomed[0], "display": snomed[1]},
            ]
        },
        "subject": {"reference": urn(patient_uuid)},
        "effectiveDateTime": obs.measured_at.isoformat(),
        # Home measurements: the patient is the performer, whether device-synced or typed in.
        "performer": [{"reference": urn(patient_uuid)}],
        # Code from KBV_VS_Base_Glucose_Concentration_Unit; the unit text is the same string,
        # as the kbv.basis example does for mg/dL.
        "valueQuantity": {"value": round(obs.value, 1), "unit": obs.unit, "system": UCUM, "code": obs.unit},
    }
    method: tuple[str, str] | None = None
    if obs.specimen == "interstitial_fluid":
        method = _GLUCOSE_CGM
    elif obs.context:
        method = _GLUCOSE_METHOD[obs.context]
    if method:
        # The MIO profile fixes the SNOMED version of this coding by pattern, and the validator
        # rejects the version the value set itself states (docs/gaps.md G15).
        res["method"] = {
            "coding": [{"system": SNOMED, "version": pack.snomed_version, "code": method[0], "display": method[1]}]
        }
    return res
