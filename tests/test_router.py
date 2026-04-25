import pytest

from app.config import settings
from app.services.classification import ClassificationResult
from app.services.patient_matcher import MatchResult
from app.services.router import RoutingDecision, route


def _cls(doc_type: str = "lab_result", confidence: float = 0.8) -> ClassificationResult:
    return ClassificationResult(doc_type=doc_type, confidence=confidence, matched_signals=["x"])


def _match(patient_id: int | None = 1, confidence: float = 0.9) -> MatchResult:
    return MatchResult(patient_id=patient_id, confidence=confidence, match_method="mrn")


# ---------------------------------------------------------------------------
# Unknown document type
# ---------------------------------------------------------------------------


class TestRouteUnknownType:
    def test_unknown_goes_to_manual_review(self):
        assert route(_cls("unknown"), _match()).queue == "manual_review"

    def test_unknown_reason_describes_issue(self):
        assert "could not be determined" in route(_cls("unknown"), _match()).reason


# ---------------------------------------------------------------------------
# Low classification confidence
# ---------------------------------------------------------------------------


class TestRouteLowConfidence:
    def test_below_threshold_goes_to_manual_review(self):
        assert route(_cls(confidence=0.3), _match()).queue == "manual_review"

    def test_reason_includes_confidence_score(self):
        assert "0.300" in route(_cls(confidence=0.3), _match()).reason

    def test_exactly_at_threshold_routes_normally(self):
        result = route(_cls("lab_result", confidence=settings.low_confidence_threshold), _match())
        assert result.queue == "provider_review"


# ---------------------------------------------------------------------------
# Administrative documents
# ---------------------------------------------------------------------------


class TestRouteAdministrative:
    def test_admin_doc_goes_to_admin_review(self):
        assert route(_cls("administrative"), _match()).queue == "admin_review"

    def test_admin_routes_without_patient_match(self):
        # Administrative docs don't require a patient match to route
        result = route(_cls("administrative"), _match(patient_id=None, confidence=0.0))
        assert result.queue == "admin_review"


# ---------------------------------------------------------------------------
# No patient match
# ---------------------------------------------------------------------------


class TestRouteNoPatientMatch:
    def test_no_patient_goes_to_manual_review(self):
        result = route(_cls("lab_result"), _match(patient_id=None, confidence=0.2))
        assert result.queue == "manual_review"

    def test_reason_includes_score(self):
        result = route(_cls("lab_result"), _match(patient_id=None, confidence=0.2))
        assert "0.200" in result.reason


# ---------------------------------------------------------------------------
# Provider-review document types
# ---------------------------------------------------------------------------


class TestRouteProviderTypes:
    @pytest.mark.parametrize("doc_type", ["lab_result", "discharge_summary", "imaging_report"])
    def test_routes_to_provider_review(self, doc_type: str):
        assert route(_cls(doc_type), _match()).queue == "provider_review"


# ---------------------------------------------------------------------------
# Coordinator-review document types
# ---------------------------------------------------------------------------


class TestRouteCoordinatorTypes:
    @pytest.mark.parametrize("doc_type", ["referral", "medication_update"])
    def test_routes_to_coordinator_review(self, doc_type: str):
        assert route(_cls(doc_type), _match()).queue == "coordinator_review"


# ---------------------------------------------------------------------------
# Return type
# ---------------------------------------------------------------------------


class TestRoutingDecisionShape:
    def test_returns_routing_decision(self):
        assert isinstance(route(_cls(), _match()), RoutingDecision)

    def test_queue_is_non_empty_string(self):
        result = route(_cls(), _match())
        assert isinstance(result.queue, str) and result.queue

    def test_reason_is_non_empty_string(self):
        result = route(_cls(), _match())
        assert isinstance(result.reason, str) and result.reason
