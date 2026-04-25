from datetime import date, datetime

from pydantic import BaseModel


class PatientBase(BaseModel):
    mrn: str
    first_name: str
    last_name: str
    dob: date


class PatientCreate(PatientBase):
    pass


class PatientRead(PatientBase):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}
