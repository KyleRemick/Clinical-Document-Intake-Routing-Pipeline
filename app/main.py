from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from app.config import settings
from app.database import Base, engine
from app.routers import documents, patients, review


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(
    title="Clinical Document Intake & Routing Pipeline",
    description="Automated intake, classification, and routing of clinical documents.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(documents.router)
app.include_router(patients.router)
app.include_router(review.router)


@app.get("/health", tags=["health"])
def health_check():
    return {"status": "ok"}
