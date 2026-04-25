from datetime import datetime

from pydantic import BaseModel


class AuditEventRead(BaseModel):
    id: int
    event_type: str
    timestamp: datetime
    details: str | None

    model_config = {"from_attributes": True}


class DocumentRead(BaseModel):
    id: int
    filename: str
    upload_at: datetime
    status: str
    extraction_method: str | None
    doc_type: str | None
    classification_confidence: float | None
    patient_id: int | None
    match_confidence: float | None
    match_method: str | None
    queue: str | None
    routing_reason: str | None
    manually_corrected: bool
    corrected_by: str | None
    corrected_at: datetime | None
    audit_events: list[AuditEventRead] = []

    model_config = {"from_attributes": True}


class DocumentListItem(BaseModel):
    id: int
    filename: str
    upload_at: datetime
    status: str
    doc_type: str | None
    queue: str | None
    routing_reason: str | None
    classification_confidence: float | None
    patient_id: int | None

    model_config = {"from_attributes": True}


class DocumentCorrection(BaseModel):
    queue: str | None = None
    doc_type: str | None = None
    patient_id: int | None = None
    corrected_by: str
