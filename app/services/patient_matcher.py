from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.patient import Patient
from app.services.metadata_parser import ParsedMetadata

logger = logging.getLogger(__name__)

# Scoring weights — must sum to 1.0
MRN_WEIGHT = 0.70
DOB_WEIGHT = 0.20
LAST_NAME_WEIGHT = 0.07
FIRST_NAME_WEIGHT = 0.03

MATCH_THRESHOLD = 0.50  # minimum confidence to consider a definitive match


@dataclass
class MatchResult:
    patient_id: int | None
    confidence: float
    match_method: str  # describes which fields contributed (e.g. "mrn", "mrn+dob")


def match(metadata: ParsedMetadata, db: Session) -> MatchResult:
    """Score all patients against parsed metadata and return the best match above threshold."""
    if not _has_any_identifiers(metadata):
        return MatchResult(patient_id=None, confidence=0.0, match_method="none")

    # Fast path: MRN exact lookup avoids a full table scan
    if metadata.mrn:
        patient = db.query(Patient).filter(Patient.mrn == metadata.mrn).first()
        if patient:
            confidence, method = _score(patient, metadata)
            if confidence >= MATCH_THRESHOLD:
                logger.debug(
                    "MRN match: patient_id=%d confidence=%.3f method=%s",
                    patient.id,
                    confidence,
                    method,
                )
                return MatchResult(
                    patient_id=patient.id,
                    confidence=round(confidence, 3),
                    match_method=method,
                )

    # Full scan — used when MRN is absent or not found
    best_id: int | None = None
    best_confidence = 0.0
    best_method = "none"

    for patient in db.query(Patient).all():
        confidence, method = _score(patient, metadata)
        if confidence > best_confidence:
            best_confidence = confidence
            best_id = patient.id
            best_method = method

    if best_confidence < MATCH_THRESHOLD:
        logger.info("No confident patient match (best_score=%.3f)", best_confidence)
        return MatchResult(
            patient_id=None,
            confidence=round(best_confidence, 3),
            match_method="none",
        )

    logger.debug(
        "Patient match: patient_id=%d confidence=%.3f method=%s",
        best_id,
        best_confidence,
        best_method,
    )
    return MatchResult(
        patient_id=best_id,
        confidence=round(best_confidence, 3),
        match_method=best_method,
    )


def _score(patient: Patient, metadata: ParsedMetadata) -> tuple[float, str]:
    score = 0.0
    methods: list[str] = []

    if metadata.mrn and patient.mrn == metadata.mrn:
        score += MRN_WEIGHT
        methods.append("mrn")

    if metadata.dob and patient.dob == metadata.dob:
        score += DOB_WEIGHT
        methods.append("dob")

    if (
        metadata.patient_last_name
        and patient.last_name.lower() == metadata.patient_last_name.lower()
    ):
        score += LAST_NAME_WEIGHT
        methods.append("last_name")

    if (
        metadata.patient_first_name
        and patient.first_name.lower() == metadata.patient_first_name.lower()
    ):
        score += FIRST_NAME_WEIGHT
        methods.append("first_name")

    return min(score, 1.0), "+".join(methods) if methods else "none"


def _has_any_identifiers(metadata: ParsedMetadata) -> bool:
    return bool(
        metadata.mrn or metadata.dob or metadata.patient_last_name or metadata.patient_first_name
    )
