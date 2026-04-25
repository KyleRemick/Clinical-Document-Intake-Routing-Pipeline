from __future__ import annotations

import logging
from dataclasses import dataclass

from app.config import settings
from app.services.classification import ClassificationResult
from app.services.patient_matcher import MatchResult

logger = logging.getLogger(__name__)

_PROVIDER_TYPES = {"lab_result", "discharge_summary", "imaging_report"}
_COORDINATOR_TYPES = {"referral", "medication_update"}
_ADMIN_TYPES = {"administrative"}


@dataclass
class RoutingDecision:
    queue: str
    reason: str


def route(classification: ClassificationResult, match: MatchResult) -> RoutingDecision:
    """Assign the document to the appropriate workflow queue."""
    if classification.doc_type == "unknown":
        return RoutingDecision(
            queue="manual_review",
            reason="document type could not be determined",
        )

    if classification.confidence < settings.low_confidence_threshold:
        return RoutingDecision(
            queue="manual_review",
            reason=f"classification confidence {classification.confidence:.3f} below threshold",
        )

    if classification.doc_type in _ADMIN_TYPES:
        return RoutingDecision(queue="admin_review", reason="administrative document")

    if match.patient_id is None:
        return RoutingDecision(
            queue="manual_review",
            reason=f"no confident patient match (best_score={match.confidence:.3f})",
        )

    if classification.doc_type in _PROVIDER_TYPES:
        return RoutingDecision(
            queue="provider_review",
            reason=f"{classification.doc_type} assigned to provider review",
        )

    if classification.doc_type in _COORDINATOR_TYPES:
        return RoutingDecision(
            queue="coordinator_review",
            reason=f"{classification.doc_type} assigned to coordinator review",
        )

    return RoutingDecision(
        queue="manual_review",
        reason=f"unrecognized document type: {classification.doc_type}",
    )
