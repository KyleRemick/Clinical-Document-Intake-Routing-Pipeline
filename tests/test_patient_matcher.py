from datetime import date

import pytest

from app.models.patient import Patient
from app.services.metadata_parser import ParsedMetadata
from app.services.patient_matcher import MATCH_THRESHOLD, match


@pytest.fixture
def patients(db):
    records = [
        Patient(mrn="MRN-T001", first_name="Alice", last_name="Johnson", dob=date(1950, 1, 15)),
        Patient(mrn="MRN-T002", first_name="Dorothy", last_name="Nguyen", dob=date(1955, 7, 22)),
        Patient(mrn="MRN-T003", first_name="Robert", last_name="Castillo", dob=date(1962, 11, 5)),
    ]
    for p in records:
        db.add(p)
    db.commit()
    for p in records:
        db.refresh(p)
    return records


# ---------------------------------------------------------------------------
# No identifiers
# ---------------------------------------------------------------------------


class TestMatchNoIdentifiers:
    def test_empty_metadata_returns_no_match(self, db):
        result = match(ParsedMetadata(), db)
        assert result.patient_id is None
        assert result.confidence == 0.0
        assert result.match_method == "none"

    def test_no_identifiers_skips_db_scan(self, patients, db):
        result = match(ParsedMetadata(), db)
        assert result.patient_id is None


# ---------------------------------------------------------------------------
# MRN fast-path
# ---------------------------------------------------------------------------


class TestMrnMatch:
    def test_mrn_exact_match_returns_patient(self, patients, db):
        result = match(ParsedMetadata(mrn="MRN-T001"), db)
        assert result.patient_id == patients[0].id

    def test_mrn_match_confidence_clears_threshold(self, patients, db):
        result = match(ParsedMetadata(mrn="MRN-T001"), db)
        assert result.confidence >= MATCH_THRESHOLD

    def test_mrn_match_method_includes_mrn(self, patients, db):
        result = match(ParsedMetadata(mrn="MRN-T001"), db)
        assert "mrn" in result.match_method

    def test_mrn_plus_dob_raises_confidence(self, patients, db):
        result = match(ParsedMetadata(mrn="MRN-T002", dob=date(1955, 7, 22)), db)
        assert result.patient_id == patients[1].id
        assert result.confidence == pytest.approx(0.70 + 0.20, abs=0.01)
        assert "mrn" in result.match_method
        assert "dob" in result.match_method

    def test_mrn_with_wrong_name_still_matches(self, patients, db):
        # MRN alone is authoritative; mismatched name doesn't block the match
        result = match(
            ParsedMetadata(mrn="MRN-T003", patient_first_name="Wrong", patient_last_name="Name"),
            db,
        )
        assert result.patient_id == patients[2].id
        assert result.confidence >= MATCH_THRESHOLD

    def test_mrn_not_in_db_falls_back_to_scan(self, patients, db):
        result = match(ParsedMetadata(mrn="MRN-UNKNOWN"), db)
        assert result.patient_id is None

    def test_empty_db_returns_no_match(self, db):
        result = match(ParsedMetadata(mrn="MRN-T001"), db)
        assert result.patient_id is None


# ---------------------------------------------------------------------------
# Full-scan fallback
# ---------------------------------------------------------------------------


class TestFullScanMatch:
    def test_name_dob_combo_below_threshold(self, patients, db):
        # last_name(0.07) + first_name(0.03) + dob(0.20) = 0.30 — under MATCH_THRESHOLD
        result = match(
            ParsedMetadata(
                patient_first_name="Alice",
                patient_last_name="Johnson",
                dob=date(1950, 1, 15),
            ),
            db,
        )
        assert result.patient_id is None
        assert result.confidence == pytest.approx(0.30, abs=0.01)

    def test_last_name_only_below_threshold(self, patients, db):
        result = match(ParsedMetadata(patient_last_name="Nguyen"), db)
        assert result.patient_id is None
        assert result.confidence < MATCH_THRESHOLD

    def test_no_field_match_confidence_is_zero(self, patients, db):
        result = match(ParsedMetadata(patient_last_name="Nonexistent"), db)
        assert result.patient_id is None
        assert result.confidence == 0.0


# ---------------------------------------------------------------------------
# MatchResult properties
# ---------------------------------------------------------------------------


class TestMatchResult:
    def test_all_fields_contribute_to_method_string(self, patients, db):
        result = match(
            ParsedMetadata(
                mrn="MRN-T002",
                dob=date(1955, 7, 22),
                patient_first_name="Dorothy",
                patient_last_name="Nguyen",
            ),
            db,
        )
        assert "mrn" in result.match_method
        assert "dob" in result.match_method
        assert "first_name" in result.match_method
        assert "last_name" in result.match_method

    def test_confidence_capped_at_one(self, patients, db):
        result = match(
            ParsedMetadata(
                mrn="MRN-T001",
                dob=date(1950, 1, 15),
                patient_first_name="Alice",
                patient_last_name="Johnson",
            ),
            db,
        )
        assert result.confidence <= 1.0

    def test_no_match_method_is_none_string(self, db):
        result = match(ParsedMetadata(), db)
        assert result.match_method == "none"
