from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.document import AuditEventType, Document, DocumentStatus
from app.schemas.document import DocumentCorrection, DocumentListItem, DocumentRead
from app.services import audit, classification, extraction, metadata_parser, patient_matcher
from app.services.router import route as determine_route

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", response_model=DocumentRead, status_code=201)
def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db)) -> DocumentRead:
    doc = Document(
        filename=file.filename or "upload",
        status=DocumentStatus.processing,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    audit.write_event(doc.id, AuditEventType.received, db, {"filename": doc.filename})

    try:
        upload_dir = Path(settings.upload_dir)
        upload_dir.mkdir(parents=True, exist_ok=True)
        file_path = upload_dir / f"{doc.id}_{doc.filename}"
        file_path.write_bytes(file.file.read())
        doc.file_path = str(file_path)

        ext_result = extraction.extract(str(file_path))
        doc.extraction_method = ext_result.method
        doc.raw_text = ext_result.text
        audit.write_event(
            doc.id,
            AuditEventType.extracted,
            db,
            {
                "method": ext_result.method,
                "page_count": ext_result.page_count,
                "char_count": len(ext_result.text),
            },
        )

        if ext_result.method == "failed":
            doc.status = DocumentStatus.failed
            doc.queue = "manual_review"
            doc.routing_reason = "text extraction failed"
            audit.write_event(doc.id, AuditEventType.failed, db, {"reason": "extraction failed"})
            db.refresh(doc)
            return DocumentRead.model_validate(doc)

        cls_result = classification.classify(ext_result.text)
        doc.doc_type = cls_result.doc_type
        doc.classification_confidence = cls_result.confidence
        audit.write_event(
            doc.id,
            AuditEventType.classified,
            db,
            {
                "doc_type": cls_result.doc_type,
                "confidence": cls_result.confidence,
                "signals": cls_result.matched_signals,
            },
        )

        meta = metadata_parser.parse(ext_result.text)
        match_result = patient_matcher.match(meta, db)
        doc.patient_id = match_result.patient_id
        doc.match_confidence = match_result.confidence
        doc.match_method = match_result.match_method
        audit.write_event(
            doc.id,
            AuditEventType.matched,
            db,
            {
                "patient_id": match_result.patient_id,
                "confidence": match_result.confidence,
                "method": match_result.match_method,
            },
        )

        routing_decision = determine_route(cls_result, match_result)
        doc.queue = routing_decision.queue
        doc.routing_reason = routing_decision.reason
        doc.status = (
            DocumentStatus.manual_review
            if routing_decision.queue == "manual_review"
            else DocumentStatus.complete
        )
        audit.write_event(
            doc.id,
            AuditEventType.routed,
            db,
            {"queue": routing_decision.queue, "reason": routing_decision.reason},
        )

        db.refresh(doc)
        return DocumentRead.model_validate(doc)

    except Exception as exc:
        logger.exception("Pipeline failed for document %d: %s", doc.id, exc)
        doc.status = DocumentStatus.failed
        doc.routing_reason = f"pipeline error: {type(exc).__name__}"
        db.commit()
        audit.write_event(doc.id, AuditEventType.failed, db, {"error": str(exc)})
        db.refresh(doc)
        return DocumentRead.model_validate(doc)


@router.get("", response_model=list[DocumentListItem])
def list_documents(
    doc_status: str | None = Query(None, alias="status"),
    queue: str | None = None,
    doc_type: str | None = None,
    db: Session = Depends(get_db),
) -> list[DocumentListItem]:
    q = db.query(Document)
    if doc_status:
        q = q.filter(Document.status == doc_status)
    if queue:
        q = q.filter(Document.queue == queue)
    if doc_type:
        q = q.filter(Document.doc_type == doc_type)
    return [DocumentListItem.model_validate(d) for d in q.order_by(Document.upload_at.desc()).all()]


@router.get("/{doc_id}", response_model=DocumentRead)
def get_document(doc_id: int, db: Session = Depends(get_db)) -> DocumentRead:
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentRead.model_validate(doc)


@router.patch("/{doc_id}/correct", response_model=DocumentRead)
def correct_document(
    doc_id: int,
    correction: DocumentCorrection,
    db: Session = Depends(get_db),
) -> DocumentRead:
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    changes: dict = {}
    if correction.queue is not None:
        doc.queue = correction.queue
        changes["queue"] = correction.queue
    if correction.doc_type is not None:
        doc.doc_type = correction.doc_type
        changes["doc_type"] = correction.doc_type
    if correction.patient_id is not None:
        doc.patient_id = correction.patient_id
        changes["patient_id"] = correction.patient_id

    doc.manually_corrected = True
    doc.corrected_by = correction.corrected_by
    doc.corrected_at = datetime.now(UTC)
    doc.status = DocumentStatus.complete
    db.commit()

    audit.write_event(
        doc.id,
        AuditEventType.corrected,
        db,
        {"corrected_by": correction.corrected_by, "changes": changes},
    )

    db.refresh(doc)
    return DocumentRead.model_validate(doc)
