from __future__ import annotations

import io
from datetime import date

import pytest

from app.models.patient import Patient

# ---------------------------------------------------------------------------
# PDF helpers (minimal inline docs for queue testing)
# ---------------------------------------------------------------------------


def _make_pdf(lines: list[str]) -> bytes:
    from fpdf import FPDF, XPos, YPos

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=10)
    for line in lines:
        pdf.cell(0, 6, text=line, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    return bytes(pdf.output())


def _unknown_pdf() -> bytes:
    return _make_pdf(["Patient: John Smith", "Date: 04/01/2026", "Facility: Some Clinic"])


def _lab_pdf(mrn: str = "MRN-10002") -> bytes:
    return _make_pdf(
        [
            "LABORATORY REPORT",
            "Patient: Dorothy Nguyen",
            f"MRN: {mrn}",
            "Date of Birth: 07/22/1955",
            "Collection Date: 04/10/2026",
            "Hemoglobin A1c: 6.8%",
            "Glucose: 118 mg/dL",
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


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _upload(client, pdf_bytes: bytes, filename: str = "doc.pdf") -> dict:
    resp = client.post(
        "/documents/upload",
        files={"file": (filename, io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert resp.status_code == 201
    return resp.json()


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
def manual_review_doc(client):
    """Upload a doc that routes to manual_review (unknown type, no patient)."""
    return _upload(client, _unknown_pdf(), "unknown.pdf")


@pytest.fixture
def provider_review_doc(client, dorothy):
    """Upload a lab result with a matching patient → provider_review."""
    return _upload(client, _lab_pdf(), "lab.pdf")


@pytest.fixture
def admin_review_doc(client):
    """Upload an admin doc → admin_review."""
    return _upload(client, _admin_pdf(), "admin.pdf")


# ---------------------------------------------------------------------------
# GET /review/queue  (manual review only)
# ---------------------------------------------------------------------------


class TestListManualReviewQueue:
    def test_empty_queue_returns_empty_list(self, client):
        resp = client.get("/review/queue")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_manual_review_doc_appears(self, client, manual_review_doc):
        resp = client.get("/review/queue")
        assert resp.status_code == 200
        ids = [d["id"] for d in resp.json()]
        assert manual_review_doc["id"] in ids

    def test_provider_review_doc_excluded(self, client, provider_review_doc):
        resp = client.get("/review/queue")
        ids = [d["id"] for d in resp.json()]
        assert provider_review_doc["id"] not in ids

    def test_admin_review_doc_excluded(self, client, admin_review_doc):
        resp = client.get("/review/queue")
        ids = [d["id"] for d in resp.json()]
        assert admin_review_doc["id"] not in ids

    def test_response_includes_routing_reason(self, client, manual_review_doc):
        items = client.get("/review/queue").json()
        item = next(d for d in items if d["id"] == manual_review_doc["id"])
        assert item["routing_reason"] is not None
        assert len(item["routing_reason"]) > 0

    def test_response_fields_present(self, client, manual_review_doc):
        item = client.get("/review/queue").json()[0]
        for field in ("id", "filename", "status", "doc_type", "queue", "routing_reason"):
            assert field in item

    def test_multiple_docs_all_appear(self, client):
        _upload(client, _unknown_pdf(), "a.pdf")
        _upload(client, _unknown_pdf(), "b.pdf")
        ids = [d["id"] for d in client.get("/review/queue").json()]
        assert len(ids) == 2


# ---------------------------------------------------------------------------
# GET /review/queue/{queue_name}
# ---------------------------------------------------------------------------


class TestListNamedQueue:
    def test_manual_review_queue_by_name(self, client, manual_review_doc):
        items = client.get("/review/queue/manual_review").json()
        ids = [d["id"] for d in items]
        assert manual_review_doc["id"] in ids

    def test_provider_review_queue(self, client, provider_review_doc):
        items = client.get("/review/queue/provider_review").json()
        ids = [d["id"] for d in items]
        assert provider_review_doc["id"] in ids

    def test_admin_review_queue(self, client, admin_review_doc):
        items = client.get("/review/queue/admin_review").json()
        ids = [d["id"] for d in items]
        assert admin_review_doc["id"] in ids

    def test_queues_are_mutually_exclusive(self, client, manual_review_doc, provider_review_doc):
        manual_ids = {d["id"] for d in client.get("/review/queue/manual_review").json()}
        provider_ids = {d["id"] for d in client.get("/review/queue/provider_review").json()}
        assert manual_ids.isdisjoint(provider_ids)

    def test_unknown_queue_name_returns_empty_list(self, client):
        # Invalid queue names return [] rather than 404 — no documents match
        resp = client.get("/review/queue/nonexistent_queue")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_empty_named_queue_returns_empty_list(self, client):
        resp = client.get("/review/queue/coordinator_review")
        assert resp.status_code == 200
        assert resp.json() == []


# ---------------------------------------------------------------------------
# Review workflow: correction moves a doc out of manual_review
# ---------------------------------------------------------------------------


class TestReviewWorkflow:
    def test_corrected_doc_leaves_manual_review(self, client, manual_review_doc):
        doc_id = manual_review_doc["id"]
        assert doc_id in [d["id"] for d in client.get("/review/queue").json()]

        client.patch(
            f"/documents/{doc_id}/correct",
            json={"queue": "admin_review", "corrected_by": "reviewer1"},
        )

        remaining_ids = [d["id"] for d in client.get("/review/queue").json()]
        assert doc_id not in remaining_ids

    def test_corrected_doc_appears_in_new_queue(self, client, manual_review_doc):
        doc_id = manual_review_doc["id"]
        client.patch(
            f"/documents/{doc_id}/correct",
            json={"queue": "provider_review", "corrected_by": "reviewer1"},
        )

        provider_ids = [d["id"] for d in client.get("/review/queue/provider_review").json()]
        assert doc_id in provider_ids

    def test_correction_audit_event_recorded(self, client, manual_review_doc):
        doc_id = manual_review_doc["id"]
        client.patch(
            f"/documents/{doc_id}/correct",
            json={"queue": "admin_review", "corrected_by": "reviewer1"},
        )

        events = client.get(f"/documents/{doc_id}").json()["audit_events"]
        corrected = [e for e in events if e["event_type"] == "corrected"]
        assert len(corrected) == 1

    def test_corrected_doc_marked_manually_corrected(self, client, manual_review_doc):
        doc_id = manual_review_doc["id"]
        resp = client.patch(
            f"/documents/{doc_id}/correct",
            json={"queue": "admin_review", "corrected_by": "reviewer1"},
        )
        assert resp.json()["manually_corrected"] is True
        assert resp.json()["corrected_by"] == "reviewer1"
