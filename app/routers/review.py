from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.document import Document
from app.schemas.document import DocumentListItem

router = APIRouter(prefix="/review", tags=["review"])


@router.get("/queue", response_model=list[DocumentListItem])
def list_manual_review_queue(db: Session = Depends(get_db)) -> list[DocumentListItem]:
    """Return all documents awaiting manual review, oldest first."""
    docs = (
        db.query(Document)
        .filter(Document.queue == "manual_review")
        .order_by(Document.upload_at.asc())
        .all()
    )
    return [DocumentListItem.model_validate(d) for d in docs]


@router.get("/queue/{queue_name}", response_model=list[DocumentListItem])
def list_named_queue(queue_name: str, db: Session = Depends(get_db)) -> list[DocumentListItem]:
    """Return all documents in the specified workflow queue, oldest first."""
    docs = (
        db.query(Document)
        .filter(Document.queue == queue_name)
        .order_by(Document.upload_at.asc())
        .all()
    )
    return [DocumentListItem.model_validate(d) for d in docs]
