#!/usr/bin/env python3
"""Seed the database with synthetic patient records from data/seed_patients.json."""

import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import Base, SessionLocal, engine
from app.models.patient import Patient

DATA_FILE = Path(__file__).parent.parent / "data" / "seed_patients.json"


def seed() -> None:
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        existing = db.query(Patient).count()
        if existing > 0:
            print(f"Patients table already has {existing} records. Skipping seed.")
            return

        with open(DATA_FILE) as f:
            records = json.load(f)

        for rec in records:
            db.add(
                Patient(
                    mrn=rec["mrn"],
                    first_name=rec["first_name"],
                    last_name=rec["last_name"],
                    dob=date.fromisoformat(rec["dob"]),
                )
            )

        db.commit()
        print(f"Seeded {len(records)} synthetic patient records.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
