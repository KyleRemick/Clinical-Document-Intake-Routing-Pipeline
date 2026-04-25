import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class DocumentStatus(enum.StrEnum):
    pending = "pending"
    processing = "processing"
    complete = "complete"
    failed = "failed"
    manual_review = "manual_review"


class ExtractionMethod(enum.StrEnum):
    pdf = "pdf"
    ocr = "ocr"
    failed = "failed"


class RoutingQueue(enum.StrEnum):
    provider_review = "provider_review"
    coordinator_review = "coordinator_review"
    admin_review = "admin_review"
    manual_review = "manual_review"


class AuditEventType(enum.StrEnum):
    received = "received"
    extracted = "extracted"
    classified = "classified"
    matched = "matched"
    routed = "routed"
    corrected = "corrected"
    failed = "failed"


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    file_path: Mapped[str | None] = mapped_column(String, nullable=True)
    upload_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    status: Mapped[str] = mapped_column(String, default=DocumentStatus.pending, nullable=False)
    extraction_method: Mapped[str | None] = mapped_column(String, nullable=True)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    doc_type: Mapped[str | None] = mapped_column(String, nullable=True)
    classification_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    patient_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("patients.id"), nullable=True
    )
    match_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    match_method: Mapped[str | None] = mapped_column(String, nullable=True)

    queue: Mapped[str | None] = mapped_column(String, nullable=True)
    routing_reason: Mapped[str | None] = mapped_column(String, nullable=True)

    manually_corrected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    corrected_by: Mapped[str | None] = mapped_column(String, nullable=True)
    corrected_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    audit_events: Mapped[list["AuditEvent"]] = relationship(
        "AuditEvent", back_populates="document", order_by="AuditEvent.timestamp"
    )


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    document_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("documents.id"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    details: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON string

    document: Mapped["Document"] = relationship("Document", back_populates="audit_events")
