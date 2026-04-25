from __future__ import annotations

import json
import logging

from sqlalchemy.orm import Session

from app.models.document import AuditEvent

logger = logging.getLogger(__name__)


def write_event(
    document_id: int,
    event_type: str,
    db: Session,
    details: dict | None = None,
) -> None:
    """Append an audit event and commit. Commits any other pending session changes too."""
    event = AuditEvent(
        document_id=document_id,
        event_type=event_type,
        details=json.dumps(details) if details else None,
    )
    db.add(event)
    db.commit()
    logger.debug("Audit event: doc_id=%d type=%s", document_id, event_type)
