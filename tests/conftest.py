from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models.patient import Patient

TEST_DATABASE_URL = "sqlite:///./test_clinical_intake.db"

test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=test_engine)
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    yield
    Base.metadata.drop_all(bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def db():
    database = TestingSessionLocal()
    try:
        yield database
    finally:
        database.close()


@pytest.fixture
def sample_patients(db):
    """Three synthetic patients for integration tests."""
    records = [
        Patient(mrn="MRN-10001", first_name="Alice", last_name="Johnson", dob=date(1950, 1, 15)),
        Patient(mrn="MRN-10002", first_name="Dorothy", last_name="Nguyen", dob=date(1955, 7, 22)),
        Patient(mrn="MRN-10003", first_name="Robert", last_name="Castillo", dob=date(1962, 11, 5)),
    ]
    for p in records:
        db.add(p)
    db.commit()
    for p in records:
        db.refresh(p)
    return records
