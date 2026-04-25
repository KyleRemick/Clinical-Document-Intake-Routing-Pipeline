from app.services.classification import ClassificationResult, classify

# ---------------------------------------------------------------------------
# Representative text samples per document type
# ---------------------------------------------------------------------------

LAB_RESULT_TEXT = """\
LABORATORY REPORT
Patient: Dorothy Nguyen
MRN: MRN-10002
Date of Birth: 07/22/1955
Collection Date: 04/10/2026
Ordering Provider: Dr. Ramona Esteves
Facility: Westlake Medical Group

TEST RESULTS
Hemoglobin A1c: 6.8%   Reference: <5.7%
Fasting Glucose: 118 mg/dL   Reference: 70-99 mg/dL
Total Cholesterol: 204 mg/dL   Reference: <200 mg/dL
Creatinine: 0.9 mg/dL
Within normal limits: eGFR, sodium, potassium
"""

DISCHARGE_SUMMARY_TEXT = """\
DISCHARGE SUMMARY
Patient: Robert Castillo
MRN: MRN-10003
Admission Date: 04/05/2026
Discharge Date: 04/09/2026
Discharging Provider: Dr. Samuel Osei

PRINCIPAL DIAGNOSIS
Community-acquired pneumonia, right lower lobe

HOSPITAL COURSE
Patient presented with productive cough and fever to 38.9C.
Treated with IV ceftriaxone and azithromycin. Afebrile x48h.

DISCHARGE MEDICATIONS
Amoxicillin-clavulanate 875mg PO BID x 5 days

FOLLOW-UP
Return to clinic in 7-10 days.
"""

REFERRAL_TEXT = """\
REFERRAL REQUEST
Referring Provider: Dr. Angela Park, MD
Patient: Thomas Bergmann
MRN: MRN-10005
Date: 04/15/2026

Referred To: Cardiology - Dr. Marcus Webb

REASON FOR REFERRAL
Patient presents with exertional chest discomfort x6 weeks.
Please evaluate for possible coronary artery disease.
Urgency: Routine
"""

IMAGING_TEXT = """\
RADIOLOGY REPORT
Patient: Helen Kowalski
MRN: MRN-10006
Study Date: 04/12/2026
Ordering Provider: Dr. Priya Nair

EXAMINATION: MRI Brain without contrast
CLINICAL INDICATION: Memory complaints, rule out vascular dementia.

FINDINGS
Mild diffuse cortical atrophy. Scattered periventricular T2/FLAIR hyperintensities.
No acute intracranial abnormality identified.

IMPRESSION
1. Mild small vessel ischemic disease.
2. No acute intracranial pathology.

Interpreting Radiologist: Dr. Yolanda Serrano, MD
"""

MEDICATION_TEXT = """\
MEDICATION RECONCILIATION
Patient: George Tanaka
MRN: MRN-10009
Date: 04/18/2026

DISCONTINUED
Metformin 500mg PO BID - discontinued due to GI intolerance

NEW PRESCRIPTIONS
Semaglutide 0.5mg SQ weekly

CONTINUED WITHOUT CHANGE
Amlodipine 5mg PO daily
Aspirin 81mg daily
"""

ADMIN_TEXT = """\
PRIOR AUTHORIZATION REQUEST
Patient: Barbara Ellison
MRN: MRN-10010
Insurance: Meridian Health Plan   Member ID: MHP-887234

CPT Code: 70553 - MRI Brain with and without contrast
ICD-10 Code: G35 - Multiple Sclerosis

Authorization request submitted on behalf of Dr. Leonard Cross, MD.
"""

POLST_TEXT = """\
PHYSICIAN ORDERS FOR LIFE-SUSTAINING TREATMENT (POLST)
Patient: Nancy Okonkwo
MRN: MRN-10018
Date of Birth: 11/17/1936
Date: 04/20/2026

DNR - Do Not Resuscitate
Advance directive reviewed and confirmed.
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _assert_classifies_as(text: str, expected_type: str, min_confidence: float = 0.2) -> None:
    result = classify(text)
    assert result.doc_type == expected_type, (
        f"Expected '{expected_type}', got '{result.doc_type}' "
        f"(confidence={result.confidence}, signals={result.matched_signals})"
    )
    assert result.confidence >= min_confidence


# ---------------------------------------------------------------------------
# Document type classification
# ---------------------------------------------------------------------------


class TestClassifyLabResult:
    def test_correct_type(self) -> None:
        _assert_classifies_as(LAB_RESULT_TEXT, "lab_result", min_confidence=0.4)

    def test_confidence_is_meaningful(self) -> None:
        result = classify(LAB_RESULT_TEXT)
        assert 0.0 < result.confidence <= 1.0

    def test_matched_signals_populated(self) -> None:
        result = classify(LAB_RESULT_TEXT)
        assert len(result.matched_signals) >= 2

    def test_lab_report_header_signal_fires(self) -> None:
        result = classify(LAB_RESULT_TEXT)
        assert "lab_report_header" in result.matched_signals


class TestClassifyDischargeSummary:
    def test_correct_type(self) -> None:
        _assert_classifies_as(DISCHARGE_SUMMARY_TEXT, "discharge_summary", min_confidence=0.5)

    def test_high_confidence_on_clear_header(self) -> None:
        result = classify(DISCHARGE_SUMMARY_TEXT)
        assert result.confidence >= 0.5

    def test_discharge_summary_header_signal_fires(self) -> None:
        result = classify(DISCHARGE_SUMMARY_TEXT)
        assert "discharge_summary_header" in result.matched_signals


class TestClassifyReferral:
    def test_correct_type(self) -> None:
        _assert_classifies_as(REFERRAL_TEXT, "referral", min_confidence=0.4)

    def test_reason_for_referral_signal_fires(self) -> None:
        result = classify(REFERRAL_TEXT)
        assert "reason_for_referral" in result.matched_signals


class TestClassifyImagingReport:
    def test_correct_type(self) -> None:
        _assert_classifies_as(IMAGING_TEXT, "imaging_report", min_confidence=0.4)

    def test_interpreting_radiologist_signal_fires(self) -> None:
        result = classify(IMAGING_TEXT)
        assert "interpreting_radiologist" in result.matched_signals


class TestClassifyMedicationUpdate:
    def test_correct_type(self) -> None:
        _assert_classifies_as(MEDICATION_TEXT, "medication_update", min_confidence=0.3)

    def test_discontinued_signal_fires(self) -> None:
        result = classify(MEDICATION_TEXT)
        assert "discontinued" in result.matched_signals


class TestClassifyAdministrative:
    def test_correct_type(self) -> None:
        _assert_classifies_as(ADMIN_TEXT, "administrative", min_confidence=0.4)

    def test_prior_auth_signal_fires(self) -> None:
        result = classify(ADMIN_TEXT)
        assert "prior_authorization" in result.matched_signals

    def test_polst_classified_as_administrative(self) -> None:
        # POLST/advance directives route through administrative for manual review
        result = classify(POLST_TEXT)
        assert result.doc_type == "administrative"
        assert "advance_directive" in result.matched_signals


# ---------------------------------------------------------------------------
# Edge and boundary cases
# ---------------------------------------------------------------------------


class TestClassifyEdgeCases:
    def test_empty_text_returns_unknown(self) -> None:
        result = classify("")
        assert result.doc_type == "unknown"
        assert result.confidence == 0.0
        assert result.matched_signals == []

    def test_whitespace_only_returns_unknown(self) -> None:
        result = classify("   \n\t  ")
        assert result.doc_type == "unknown"

    def test_generic_clinical_noise_returns_unknown(self) -> None:
        result = classify("Patient: John Smith\nDate: 04/01/2026\nFacility: Some Clinic")
        assert result.doc_type == "unknown"

    def test_returns_classification_result_type(self) -> None:
        result = classify(LAB_RESULT_TEXT)
        assert isinstance(result, ClassificationResult)
        assert isinstance(result.doc_type, str)
        assert isinstance(result.confidence, float)
        assert isinstance(result.matched_signals, list)

    def test_confidence_bounded_between_zero_and_one(self) -> None:
        for text in [LAB_RESULT_TEXT, DISCHARGE_SUMMARY_TEXT, REFERRAL_TEXT, ""]:
            result = classify(text)
            assert 0.0 <= result.confidence <= 1.0


# ---------------------------------------------------------------------------
# Integration: sample PDFs classify correctly end-to-end
# ---------------------------------------------------------------------------


class TestClassifyFromSampleDocs:
    """Read the generated sample PDFs via pdfplumber and verify classification."""

    def _extract(self, filename: str) -> str:
        import pdfplumber

        path = f"sample_docs/{filename}"
        with pdfplumber.open(path) as pdf:
            return "\n".join(p.extract_text() or "" for p in pdf.pages)

    def test_lab_result_pdf(self) -> None:
        _assert_classifies_as(self._extract("lab_result.pdf"), "lab_result")

    def test_discharge_summary_pdf(self) -> None:
        _assert_classifies_as(self._extract("discharge_summary.pdf"), "discharge_summary")

    def test_referral_pdf(self) -> None:
        _assert_classifies_as(self._extract("referral.pdf"), "referral")

    def test_imaging_report_pdf(self) -> None:
        _assert_classifies_as(self._extract("imaging_report.pdf"), "imaging_report")

    def test_medication_update_pdf(self) -> None:
        _assert_classifies_as(self._extract("medication_update.pdf"), "medication_update")

    def test_administrative_pdf(self) -> None:
        _assert_classifies_as(self._extract("administrative.pdf"), "administrative")
