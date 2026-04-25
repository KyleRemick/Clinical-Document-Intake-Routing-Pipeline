from datetime import date

from app.services.metadata_parser import ParsedMetadata, parse

# ---------------------------------------------------------------------------
# Fixtures — realistic synthetic document text blocks
# ---------------------------------------------------------------------------

LAB_TEXT = """\
LABORATORY REPORT
Patient: Dorothy Nguyen
MRN: MRN-10002
Date of Birth: 07/22/1955
Collection Date: 04/10/2026
Ordering Provider: Dr. Ramona Esteves
Facility: Westlake Medical Group

Hemoglobin A1c: 6.8%   Reference: <5.7%
"""

DISCHARGE_TEXT = """\
DISCHARGE SUMMARY
Patient: Robert Castillo
MRN: MRN-10003
Date of Birth: 11/05/1962
Admission Date: 04/05/2026
Discharge Date: 04/09/2026
Discharging Provider: Dr. Samuel Osei
Facility: Northbrook Regional Hospital
"""

REFERRAL_TEXT = """\
REFERRAL REQUEST
Referring Provider: Dr. Angela Park, MD
Patient: Thomas Bergmann
MRN: MRN-10005
Date of Birth: 09/18/1957
Date: 04/15/2026
"""

IMAGING_TEXT = """\
RADIOLOGY REPORT
Patient: Helen Kowalski
MRN: MRN-10006
Date of Birth: 06/03/1944
Study Date: 04/12/2026
Facility: Eastside Imaging Center
Interpreting Radiologist: Dr. Yolanda Serrano, MD
"""


# ---------------------------------------------------------------------------
# MRN extraction
# ---------------------------------------------------------------------------


class TestExtractMrn:
    def test_standard_mrn_label(self) -> None:
        result = parse("Patient: Jane Doe\nMRN: MRN-10001\n")
        assert result.mrn == "MRN-10001"

    def test_mrn_with_hash(self) -> None:
        result = parse("MRN# ABC-123\n")
        assert result.mrn == "ABC-123"

    def test_medical_record_number_label(self) -> None:
        result = parse("Medical Record Number: MRN-10005\n")
        assert result.mrn == "MRN-10005"

    def test_numeric_mrn(self) -> None:
        result = parse("MRN: 789456\n")
        assert result.mrn == "789456"

    def test_mrn_absent_returns_none(self) -> None:
        result = parse("Patient: James Whitfield\nDOB: 03/14/1948\n")
        assert result.mrn is None


# ---------------------------------------------------------------------------
# Name extraction
# ---------------------------------------------------------------------------


class TestExtractName:
    def test_first_last_format(self) -> None:
        result = parse("Patient: Dorothy Nguyen\nMRN: MRN-10002\n")
        assert result.patient_first_name == "Dorothy"
        assert result.patient_last_name == "Nguyen"

    def test_patient_name_label(self) -> None:
        result = parse("Patient Name: James Whitfield\n")
        assert result.patient_first_name == "James"
        assert result.patient_last_name == "Whitfield"

    def test_last_first_format(self) -> None:
        result = parse("Patient: Castillo, Robert\n")
        assert result.patient_first_name == "Robert"
        assert result.patient_last_name == "Castillo"

    def test_hyphenated_last_name(self) -> None:
        result = parse("Patient: Carol Smith-Jones\n")
        assert result.patient_first_name == "Carol"
        assert result.patient_last_name == "Smith-Jones"

    def test_name_absent_returns_none(self) -> None:
        result = parse("MRN: MRN-10001\nDOB: 01/01/1950\n")
        assert result.patient_first_name is None
        assert result.patient_last_name is None


# ---------------------------------------------------------------------------
# DOB extraction
# ---------------------------------------------------------------------------


class TestExtractDob:
    def test_slash_format(self) -> None:
        result = parse("Date of Birth: 07/22/1955\n")
        assert result.dob == date(1955, 7, 22)

    def test_dob_abbreviation(self) -> None:
        result = parse("DOB: 03/14/1948\n")
        assert result.dob == date(1948, 3, 14)

    def test_iso_format(self) -> None:
        result = parse("DOB: 1962-11-05\n")
        assert result.dob == date(1962, 11, 5)

    def test_dash_format(self) -> None:
        result = parse("Date of Birth: 06-03-1944\n")
        assert result.dob == date(1944, 6, 3)

    def test_written_month_format(self) -> None:
        result = parse("Date of Birth: July 22, 1955\n")
        assert result.dob == date(1955, 7, 22)

    def test_dob_absent_returns_none(self) -> None:
        result = parse("Patient: Helen Kowalski\nMRN: MRN-10006\n")
        assert result.dob is None


# ---------------------------------------------------------------------------
# Document date extraction
# ---------------------------------------------------------------------------


class TestExtractDocumentDate:
    def test_collection_date(self) -> None:
        result = parse("Collection Date: 04/10/2026\n")
        assert result.document_date == date(2026, 4, 10)

    def test_study_date(self) -> None:
        result = parse("Study Date: 04/12/2026\n")
        assert result.document_date == date(2026, 4, 12)

    def test_discharge_date(self) -> None:
        result = parse("Discharge Date: 04/09/2026\n")
        assert result.document_date == date(2026, 4, 9)

    def test_generic_date_label(self) -> None:
        result = parse("Date: 04/15/2026\n")
        assert result.document_date == date(2026, 4, 15)

    def test_date_absent_returns_none(self) -> None:
        result = parse("Patient: Thomas Bergmann\nMRN: MRN-10005\n")
        assert result.document_date is None


# ---------------------------------------------------------------------------
# Facility extraction
# ---------------------------------------------------------------------------


class TestExtractFacility:
    def test_facility_label(self) -> None:
        result = parse("Facility: Westlake Medical Group\n")
        assert result.facility_name == "Westlake Medical Group"

    def test_hospital_label(self) -> None:
        result = parse("Hospital: Northbrook Regional Hospital\n")
        assert result.facility_name == "Northbrook Regional Hospital"

    def test_provider_label_fallback(self) -> None:
        result = parse("Ordering Provider: Dr. Ramona Esteves\n")
        assert result.facility_name is not None
        assert "Esteves" in result.facility_name

    def test_facility_absent_returns_none(self) -> None:
        result = parse("Patient: Betty Lindqvist\nMRN: MRN-10020\n")
        assert result.facility_name is None


# ---------------------------------------------------------------------------
# found_fields and ParsedMetadata structure
# ---------------------------------------------------------------------------


class TestParsedMetadata:
    def test_found_fields_complete(self) -> None:
        result = parse(LAB_TEXT)
        fields = result.found_fields()
        assert "mrn" in fields
        assert "first_name" in fields
        assert "last_name" in fields
        assert "dob" in fields

    def test_found_fields_empty_on_blank_text(self) -> None:
        result = parse("")
        assert result.found_fields() == []

    def test_returns_parsed_metadata_type(self) -> None:
        result = parse(LAB_TEXT)
        assert isinstance(result, ParsedMetadata)

    def test_all_fields_none_on_empty_text(self) -> None:
        result = parse("")
        assert result.mrn is None
        assert result.patient_first_name is None
        assert result.patient_last_name is None
        assert result.dob is None
        assert result.document_date is None
        assert result.facility_name is None


# ---------------------------------------------------------------------------
# Integration: parse full synthetic document text blocks
# ---------------------------------------------------------------------------


class TestParseFullDocuments:
    def test_lab_document(self) -> None:
        result = parse(LAB_TEXT)
        assert result.mrn == "MRN-10002"
        assert result.patient_first_name == "Dorothy"
        assert result.patient_last_name == "Nguyen"
        assert result.dob == date(1955, 7, 22)
        assert result.document_date == date(2026, 4, 10)

    def test_discharge_document(self) -> None:
        result = parse(DISCHARGE_TEXT)
        assert result.mrn == "MRN-10003"
        assert result.patient_first_name == "Robert"
        assert result.patient_last_name == "Castillo"
        assert result.dob == date(1962, 11, 5)

    def test_referral_document(self) -> None:
        result = parse(REFERRAL_TEXT)
        assert result.mrn == "MRN-10005"
        assert result.patient_first_name == "Thomas"
        assert result.patient_last_name == "Bergmann"

    def test_imaging_document(self) -> None:
        result = parse(IMAGING_TEXT)
        assert result.mrn == "MRN-10006"
        assert result.patient_first_name == "Helen"
        assert result.patient_last_name == "Kowalski"
        assert result.document_date == date(2026, 4, 12)
        assert result.facility_name is not None
