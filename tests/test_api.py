from __future__ import annotations

import io
from datetime import date

import pytest

from app.models.patient import Patient

# ---------------------------------------------------------------------------
# PDF helpers
# ---------------------------------------------------------------------------


def _make_pdf(lines: list[str]) -> bytes:
    from fpdf import FPDF, XPos, YPos

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=10)
    for line in lines:
        pdf.cell(0, 6, text=line, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    return bytes(pdf.output())


def _lab_pdf() -> bytes:
    return _make_pdf(
        [
            "LABORATORY REPORT",
            "Patient: Dorothy Nguyen",
            "MRN: MRN-10002",
            "Date of Birth: 07/22/1955",
            "Collection Date: 04/10/2026",
            "Facility: Westlake Medical Group",
            "",
            "Hemoglobin A1c: 6.8%",
            "Glucose: 118 mg/dL",
            "Cholesterol: 204 mg/dL",
            "Within normal limits: eGFR, sodium",
        ]
    )


def _admin_pdf() -> bytes:
    return _make_pdf(
        [
            "PRIOR AUTHORIZATION REQUEST",
            "Patient: Barbara Ellison",
            "Insurance Plan: Meridian Health Plan",
            "Member ID: MHP-887234",
            "Auth Number: PA-12345",
            "CPT Code: 70553 - MRI Brain",
            "ICD-10 Code: G35 - Multiple Sclerosis",
        ]
    )


def _unknown_pdf() -> bytes:
    return _make_pdf(["Patient: John Smith", "Date: 04/01/2026", "Facility: Some Clinic"])


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def dorothy(db):
    patient = Patient(
        mrn="MRN-10002", first_name="Dorothy", last_name="Nguyen", dob=date(1955, 7, 22)
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient


@pytest.fixture
def uploaded_lab(client, dorothy):
    resp = client.post(
        "/documents/upload",
        files={"file": ("lab_result.pdf", io.BytesIO(_lab_pdf()), "application/pdf")},
    )
    assert resp.status_code == 201
    return resp.json()


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


class TestHealth:
    def test_returns_ok(self, client):
        assert client.get("/health").json() == {"status": "ok"}

    def test_status_200(self, client):
        assert client.get("/health").status_code == 200


# ---------------------------------------------------------------------------
# Patients — list
# ---------------------------------------------------------------------------


class TestListPatients:
    def test_empty_db_returns_empty_list(self, client):
        resp = client.get("/patients")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_returns_all_seeded_patients(self, client, sample_patients):
        resp = client.get("/patients")
        assert resp.status_code == 200
        assert len(resp.json()) == len(sample_patients)

    def test_response_fields_present(self, client, sample_patients):
        patient = client.get("/patients").json()[0]
        for field in ("id", "mrn", "first_name", "last_name", "dob"):
            assert field in patient


# ---------------------------------------------------------------------------
# Patients — detail
# ---------------------------------------------------------------------------


class TestGetPatient:
    def test_returns_correct_patient(self, client, sample_patients):
        pid = sample_patients[0].id
        resp = client.get(f"/patients/{pid}")
        assert resp.status_code == 200
        assert resp.json()["id"] == pid

    def test_not_found_returns_404(self, client):
        assert client.get("/patients/99999").status_code == 404


# ---------------------------------------------------------------------------
# Document upload
# ---------------------------------------------------------------------------


class TestDocumentUpload:
    def test_upload_returns_201(self, client, dorothy):
        resp = client.post(
            "/documents/upload",
            files={"file": ("lab.pdf", io.BytesIO(_lab_pdf()), "application/pdf")},
        )
        assert resp.status_code == 201

    def test_upload_classifies_as_lab_result(self, uploaded_lab):
        assert uploaded_lab["doc_type"] == "lab_result"

    def test_upload_matches_dorothy(self, uploaded_lab, dorothy):
        assert uploaded_lab["patient_id"] == dorothy.id

    def test_upload_routes_to_provider_review(self, uploaded_lab):
        assert uploaded_lab["queue"] == "provider_review"

    def test_upload_status_is_complete(self, uploaded_lab):
        assert uploaded_lab["status"] == "complete"

    def test_upload_returns_document_id(self, uploaded_lab):
        assert isinstance(uploaded_lab["id"], int)

    def test_upload_has_full_audit_trail(self, uploaded_lab):
        event_types = {e["event_type"] for e in uploaded_lab["audit_events"]}
        assert {"received", "extracted", "classified", "matched", "routed"} <= event_types

    def test_upload_unknown_doc_routes_to_manual_review(self, client):
        resp = client.post(
            "/documents/upload",
            files={"file": ("unknown.pdf", io.BytesIO(_unknown_pdf()), "application/pdf")},
        )
        assert resp.status_code == 201
        assert resp.json()["queue"] == "manual_review"

    def test_upload_admin_doc_routes_to_admin_review(self, client):
        resp = client.post(
            "/documents/upload",
            files={"file": ("admin.pdf", io.BytesIO(_admin_pdf()), "application/pdf")},
        )
        assert resp.status_code == 201
        assert resp.json()["queue"] == "admin_review"

    def test_upload_no_patient_match_routes_to_manual_review(self, client):
        # Lab result but no matching patient in DB
        resp = client.post(
            "/documents/upload",
            files={"file": ("lab.pdf", io.BytesIO(_lab_pdf()), "application/pdf")},
        )
        assert resp.status_code == 201
        assert resp.json()["queue"] == "manual_review"


# ---------------------------------------------------------------------------
# Document list
# ---------------------------------------------------------------------------


class TestListDocuments:
    def test_empty_db_returns_empty_list(self, client):
        resp = client.get("/documents")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_returns_uploaded_documents(self, client, uploaded_lab):
        resp = client.get("/documents")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_filter_by_status(self, client, uploaded_lab):
        docs = client.get("/documents", params={"status": "complete"}).json()
        assert all(d["status"] == "complete" for d in docs)

    def test_filter_by_queue(self, client, uploaded_lab):
        docs = client.get("/documents", params={"queue": "provider_review"}).json()
        assert all(d["queue"] == "provider_review" for d in docs)

    def test_filter_by_doc_type(self, client, uploaded_lab):
        docs = client.get("/documents", params={"doc_type": "lab_result"}).json()
        assert all(d["doc_type"] == "lab_result" for d in docs)

    def test_filter_excludes_non_matching(self, client, uploaded_lab):
        docs = client.get("/documents", params={"status": "failed"}).json()
        assert docs == []


# ---------------------------------------------------------------------------
# Document detail
# ---------------------------------------------------------------------------


class TestGetDocument:
    def test_returns_full_record(self, client, uploaded_lab):
        resp = client.get(f"/documents/{uploaded_lab['id']}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == uploaded_lab["id"]
        assert body["doc_type"] == "lab_result"
        assert body["classification_confidence"] is not None

    def test_includes_audit_trail(self, client, uploaded_lab):
        resp = client.get(f"/documents/{uploaded_lab['id']}")
        assert len(resp.json()["audit_events"]) >= 5

    def test_not_found_returns_404(self, client):
        assert client.get("/documents/99999").status_code == 404


# ---------------------------------------------------------------------------
# Document correction
# ---------------------------------------------------------------------------


class TestDocumentCorrection:
    def test_correct_queue(self, client, uploaded_lab):
        resp = client.patch(
            f"/documents/{uploaded_lab['id']}/correct",
            json={"queue": "admin_review", "corrected_by": "reviewer1"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["queue"] == "admin_review"
        assert body["manually_corrected"] is True
        assert body["corrected_by"] == "reviewer1"

    def test_correct_doc_type(self, client, uploaded_lab):
        resp = client.patch(
            f"/documents/{uploaded_lab['id']}/correct",
            json={"doc_type": "referral", "corrected_by": "reviewer1"},
        )
        assert resp.status_code == 200
        assert resp.json()["doc_type"] == "referral"

    def test_correction_status_becomes_complete(self, client, uploaded_lab):
        resp = client.patch(
            f"/documents/{uploaded_lab['id']}/correct",
            json={"queue": "admin_review", "corrected_by": "reviewer1"},
        )
        assert resp.json()["status"] == "complete"

    def test_correction_adds_corrected_audit_event(self, client, uploaded_lab):
        client.patch(
            f"/documents/{uploaded_lab['id']}/correct",
            json={"queue": "admin_review", "corrected_by": "reviewer1"},
        )
        events = client.get(f"/documents/{uploaded_lab['id']}").json()["audit_events"]
        assert any(e["event_type"] == "corrected" for e in events)

    def test_correct_not_found_returns_404(self, client):
        resp = client.patch(
            "/documents/99999/correct",
            json={"queue": "admin_review", "corrected_by": "reviewer1"},
        )
        assert resp.status_code == 404
