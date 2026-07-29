"""
Turns raw report text into structured lab results + patient info.

Deliberately regex-based, not NLP-based: lab reports are semi-tabular
("Test Name .... Value .... Unit .... Range"), so a name->number pattern
match finds every value we need without a transformer model in the loop.

# ponytail: patient-info fields use single hand-written regexes, not a
# trained NER model. Ceiling: unusual header layouts (info in a table
# image, non-English labels) won't match. Upgrade path: if real-world
# reports miss these fields often, swap in spaCy's NER for this function
# only -- extract_lab_values() below is unaffected either way.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from models.lab_reference import LAB_TESTS


@dataclass
class LabResult:
    test: str          # key in LAB_TESTS
    label: str          # human display name
    value: float
    unit: str
    low: float
    high: float
    flag: str           # normal | low | high | critical


@dataclass
class ExtractionResult:
    patient_info: dict = field(default_factory=dict)
    lab_results: list[LabResult] = field(default_factory=list)


_NUM = r"([-+]?\d+\.?\d*)"

_PATIENT_PATTERNS = {
    "name": r"(?:patient\s*name|name)\s*[:\-]\s*([A-Za-z][A-Za-z .]{2,40})",
    "age": r"age\s*[:\-]\s*(\d{1,3})",
    "gender": r"(?:gender|sex)\s*[:\-]\s*(male|female|m|f)\b",
    "doctor": r"(?:doctor|physician|referred\s+by)\s*[:\-]\s*(?:dr\.?\s*)?([A-Za-z][A-Za-z .]{2,40})",
    "hospital": r"(?:hospital|lab(?:oratory)?|clinic)\s*[:\-]\s*([A-Za-z][A-Za-z0-9 .,&-]{2,60})",
    "report_date": r"(?:report\s*date|date)\s*[:\-]\s*(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})",
}


def extract_patient_info(text: str) -> dict:
    info = {}
    for field_name, pattern in _PATIENT_PATTERNS.items():
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            info[field_name] = m.group(1).strip().rstrip(",")
    return info


def _flag_value(value: float, spec: dict) -> str:
    if spec.get("critical_low") is not None and value <= spec["critical_low"]:
        return "critical"
    if spec.get("critical_high") is not None and value >= spec["critical_high"]:
        return "critical"
    if value < spec["low"]:
        return "low"
    if value > spec["high"]:
        return "high"
    return "normal"


def extract_lab_values(text: str) -> list[LabResult]:
    results = []
    seen = set()
    for test_key, spec in LAB_TESTS.items():
        if test_key in seen:
            continue
        for alias in spec["aliases"]:
            # name ... number (first number after the label on the same line)
            pattern = rf"{alias}[^\n\d-]{{0,25}}{_NUM}"
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                try:
                    value = float(m.group(1))
                except ValueError:
                    continue
                results.append(LabResult(
                    test=test_key,
                    label=test_key.replace("_", " ").title(),
                    value=value,
                    unit=spec["unit"],
                    low=spec["low"],
                    high=spec["high"],
                    flag=_flag_value(value, spec),
                ))
                seen.add(test_key)
                break
    return results


def extract_all(text: str) -> ExtractionResult:
    return ExtractionResult(
        patient_info=extract_patient_info(text),
        lab_results=extract_lab_values(text),
    )


# Words that show up in essentially every real lab report but rarely
# together in unrelated documents -- used only to catch "this obviously
# isn't a medical report" (a photo of a receipt, a random PDF, etc.).
_MEDICAL_KEYWORDS = re.compile(
    r"\b(patient|report|specimen|laboratory|lab\s*results?|reference\s*range|"
    r"test\s*name|diagnos|physician|hospital|clinic|mg/dL|g/dL|mmol|normal\s*range)\b",
    re.IGNORECASE,
)


def looks_like_medical_report(result: "ExtractionResult", raw_text: str) -> bool:
    """
    # ponytail: keyword/marker heuristic, not a trained classifier.
    # Ceiling: an unusually-formatted real report with none of these words
    # could be rejected; a document that happens to mention "patient" and
    # a unit could pass. Upgrade path: once misclassified examples pile up,
    # replace this with a small trained text classifier -- same signature
    # (ExtractionResult, str) -> bool, nothing else in the app changes.
    """
    if result.lab_results:
        return True  # found actual values we recognize -- strongest signal
    if len(result.patient_info) >= 2 and _MEDICAL_KEYWORDS.search(raw_text):
        return True
    if len(_MEDICAL_KEYWORDS.findall(raw_text)) >= 3:
        return True
    return False
