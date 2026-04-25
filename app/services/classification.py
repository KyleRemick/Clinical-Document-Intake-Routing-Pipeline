from __future__ import annotations

import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)

UNKNOWN = "unknown"
MIN_CONFIDENCE = 0.10  # below this threshold, result is "unknown" regardless of top match


@dataclass(frozen=True)
class Signal:
    name: str
    pattern: str
    weight: float

    def matches(self, text: str) -> bool:
        return bool(re.search(self.pattern, text, re.IGNORECASE))


@dataclass
class ClassificationResult:
    doc_type: str
    confidence: float
    matched_signals: list[str]


# ---------------------------------------------------------------------------
# Signal definitions
# Each signal has a human-readable name (for audit logging), a regex pattern,
# and a weight. Higher weight = stronger indicator of that document type.
# ---------------------------------------------------------------------------

_LAB_RESULT: list[Signal] = [
    Signal("lab_report_header", r"lab(?:oratory)?\s+(?:report|result|findings?)", 0.8),
    Signal("reference_range", r"reference\s+(?:range|interval|values?)", 0.8),
    Signal("lab_units", r"\b(?:mg/dl|meq/l|mmol/l|ng/ml|iu/l|u/l|g/dl|miu/ml)\b", 0.6),
    Signal(
        "common_analyte",
        r"\b(?:hemoglobin|hgb|hba1c|glucose|cholesterol|creatinine|egfr|bun|"
        r"sodium|potassium|wbc|rbc|platelet|ferritin|tsh|psa|albumin|bilirubin)\b",
        0.6,
    ),
    Signal("collection_date", r"collection\s+(?:date|time)", 0.5),
    Signal("specimen", r"\bspecimen\b", 0.4),
    Signal("metabolic_panel", r"\b(?:basic|comprehensive)\s+metabolic\s+panel\b", 0.7),
    Signal("within_normal_limits", r"within\s+normal\s+(?:limits|range)\b", 0.5),
]

_REFERRAL: list[Signal] = [
    Signal("referral_header", r"\breferral\s+(?:request|letter|form)?\b", 0.9),
    Signal("referring_provider", r"referring\s+(?:provider|physician|doctor|md|do)\b", 0.8),
    Signal("referred_to", r"\breferred\s+to\b", 0.8),
    Signal("reason_for_referral", r"reason\s+for\s+referral", 0.9),
    Signal("please_evaluate", r"\bplease\s+(?:evaluate|see|assess|consult)\b", 0.5),
    Signal("consultation_request", r"\bconsult(?:ation)?\s+(?:request|referral)?\b", 0.6),
    Signal("urgency_level", r"\burgency[:\s]+(?:routine|urgent|emergent)\b", 0.4),
]

_DISCHARGE_SUMMARY: list[Signal] = [
    Signal("discharge_summary_header", r"\bdischarge\s+summary\b", 1.0),
    Signal("admission_date", r"\b(?:admitted|admission)\s+(?:date|on|to)\b", 0.7),
    Signal(
        "discharge_date",
        r"\bdischarge\s+(?:date|condition|medications?|instructions?|disposition)\b",
        0.8,
    ),
    Signal("principal_diagnosis", r"\b(?:principal|primary|final|admitting)\s+diagnosis\b", 0.7),
    Signal("hospital_course", r"\bhospital\s+course\b", 0.9),
    Signal("discharge_medications", r"\bdischarge\s+medications?\b", 0.7),
    Signal(
        "follow_up",
        r"\bfollow[- ]up\s+(?:with|instructions?|care|appointment)\b",
        0.4,
    ),
    Signal(
        "discharging_provider",
        r"\b(?:discharging|attending)\s+(?:provider|physician|doctor)\b",
        0.5,
    ),
]

_IMAGING_REPORT: list[Signal] = [
    Signal("radiology_header", r"\bradiology\s+report\b", 0.9),
    Signal(
        "imaging_modality",
        r"\b(?:mri|ct\s+scan|x[- ]ray|ultrasound|mammograph|pet\s+scan|"
        r"fluoroscop|echocardiograph|dexa|bone\s+scan|nuclear\s+medicine)\b",
        0.8,
    ),
    Signal("impression_section", r"\bimpression[:\s]", 0.6),
    Signal("clinical_indication", r"\bclinical\s+indication[:\s]", 0.6),
    Signal(
        "interpreting_radiologist",
        r"\binterpreting\s+(?:radiologist|physician)\b",
        0.8,
    ),
    Signal(
        "no_acute_findings",
        r"\bno\s+acute\s+(?:findings?|abnormality|intracranial|cardiopulmonary)\b",
        0.5,
    ),
    Signal("findings_section", r"\bfindings?[:\s]", 0.4),
    Signal("examination_type", r"\bexamination[:\s]", 0.4),
]

_MEDICATION_UPDATE: list[Signal] = [
    Signal(
        "medication_reconciliation_header",
        r"\bmedication\s+(?:reconciliation|update|list|change|management)\b",
        0.9,
    ),
    Signal(
        "new_medication",
        r"\b(?:new|added|start(?:ing)?|initiated)\s+(?:medication|prescription|rx)\b",
        0.7,
    ),
    Signal("discontinued", r"\b(?:discontinued|stopped|discontinue)\b", 0.7),
    Signal(
        "dosage_change",
        r"\b(?:dosage|dose)\s+(?:change|adjustment|increase|decrease)\b",
        0.6,
    ),
    Signal("medication_route", r"\b(?:po|iv|sq|im|sl|topical|transdermal|inhaled)\b", 0.4),
    Signal("medication_frequency", r"\b(?:bid|tid|qid|prn|q\d+h)\b", 0.4),
    Signal("continued_without_change", r"\bcontinued?\s+without\s+change\b", 0.6),
]

_ADMINISTRATIVE: list[Signal] = [
    Signal("prior_authorization", r"\bprior\s+authorization\b", 0.9),
    Signal("insurance_plan", r"\binsurance\s+(?:company|plan|authorization|coverage)\b", 0.7),
    Signal("member_id", r"\b(?:member|policy|group)\s+(?:id|number|#)\b", 0.6),
    Signal(
        "authorization_number",
        r"\bauth(?:orization)?\s+(?:number|request|approval|denial)\b",
        0.8,
    ),
    Signal("cpt_code", r"\bcpt\s+code[:\s]", 0.8),
    Signal("icd_code", r"\bicd[- ]?(?:9|10)[- ]?(?:cm)?\s+(?:code)?[:\s]", 0.7),
    Signal("billing_terms", r"\b(?:billing|claims?|reimbursement)\b", 0.4),
    Signal("advance_directive", r"\b(?:polst|molst|dnr|advance\s+directive|living\s+will)\b", 0.8),
    Signal("consent_form", r"\b(?:consent\s+form|patient\s+consent|authorization\s+form)\b", 0.5),
]

SIGNALS: dict[str, list[Signal]] = {
    "lab_result": _LAB_RESULT,
    "referral": _REFERRAL,
    "discharge_summary": _DISCHARGE_SUMMARY,
    "imaging_report": _IMAGING_REPORT,
    "medication_update": _MEDICATION_UPDATE,
    "administrative": _ADMINISTRATIVE,
}


def classify(text: str) -> ClassificationResult:
    """
    Score the text against each document type's signal set and return the
    best match. Returns "unknown" when no type clears MIN_CONFIDENCE.
    """
    if not text.strip():
        return ClassificationResult(doc_type=UNKNOWN, confidence=0.0, matched_signals=[])

    best_type = UNKNOWN
    best_confidence = 0.0
    best_signals: list[str] = []

    for doc_type, signals in SIGNALS.items():
        matched = [s for s in signals if s.matches(text)]
        if not matched:
            continue

        max_possible = sum(s.weight for s in signals)
        raw_score = sum(s.weight for s in matched)
        confidence = min(raw_score / max_possible, 1.0)

        if confidence > best_confidence:
            best_confidence = confidence
            best_type = doc_type
            best_signals = [s.name for s in matched]

    if best_confidence < MIN_CONFIDENCE:
        best_type = UNKNOWN

    logger.debug(
        "Classified as '%s' (confidence=%.3f, signals=%s)",
        best_type,
        best_confidence,
        best_signals,
    )

    return ClassificationResult(
        doc_type=best_type,
        confidence=round(best_confidence, 3),
        matched_signals=best_signals,
    )
