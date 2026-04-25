from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import date, datetime

logger = logging.getLogger(__name__)

# Date formats tried in order when parsing extracted date strings
_DATE_FORMATS = [
    "%m/%d/%Y",
    "%m-%d-%Y",
    "%m.%d.%Y",
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%B %d, %Y",
    "%b %d, %Y",
    "%B %d %Y",
    "%b %d %Y",
    "%d %B %Y",
    "%d %b %Y",
    "%m/%d/%y",
]

_MRN_PATTERNS = [
    r"MRN[:\s#]+([A-Z0-9][A-Z0-9\-]{2,19})\b",
    r"Medical\s+Record\s+(?:Number|No\.?|#)[:\s]+([A-Z0-9][A-Z0-9\-]{2,19})\b",
    r"(?:Patient|Pt\.?)\s+(?:ID|Number)[:\s]+([A-Z0-9][A-Z0-9\-]{2,19})\b",
]

# Each entry is (pattern, arg_order) where arg_order is "first_last" or "last_first"
# [a-zA-Z'\-]+ allows hyphenated names like Smith-Jones (capital after hyphen is valid)
_NAME_PATTERNS: list[tuple[str, str]] = [
    # "Patient: First Last" or "Patient Name: First Last"
    (
        r"Patient(?:\s+Name)?[:\s]+([A-Z][a-zA-Z'\-]+)\s+([A-Z][a-zA-Z'\-]+)",
        "first_last",
    ),
    # "Patient: Last, First"
    (
        r"Patient(?:\s+Name)?[:\s]+([A-Z][a-zA-Z'\-]+),\s*([A-Z][a-zA-Z'\-]+)",
        "last_first",
    ),
    # "Name: First Last"
    (
        r"\bName[:\s]+([A-Z][a-zA-Z'\-]+)\s+([A-Z][a-zA-Z'\-]+)",
        "first_last",
    ),
]

_DOB_PATTERNS = [
    r"(?:DOB|Date\s+of\s+Birth|Birth\s+Date|D\.O\.B\.)[:\s]+(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})",
    r"(?:DOB|Date\s+of\s+Birth)[:\s]+([A-Za-z]+\s+\d{1,2},?\s+\d{4})",
    r"(?:DOB|D\.O\.B\.)[:\s]+(\d{4}[/\-\.]\d{1,2}[/\-\.]\d{1,2})",
]

_DOCUMENT_DATE_PATTERNS = [
    r"(?:Collection|Study|Report|Document|Service|Visit)\s+Date[:\s]+(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})",
    r"(?:Discharge|Admission)\s+Date[:\s]+(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})",
    r"(?<!\w)Date[:\s]+(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})",
]

_FACILITY_PATTERNS = [
    r"(?:Facility|Hospital|Clinic|Center|Medical\s+Group|Practice|Institute)[:\s]+([A-Z][^\n]{4,60})",
]

_PROVIDER_PATTERNS = [
    r"(?:Ordering|Referring|Attending|Discharging|Requesting)\s+Provider[:\s]+(?:Dr\.?\s+)?([A-Z][^\n]{2,60})",
    r"Interpreting\s+Radiologist[:\s]+(?:Dr\.?\s+)?([A-Z][^\n]{2,60})",
]


@dataclass
class ParsedMetadata:
    patient_first_name: str | None = None
    patient_last_name: str | None = None
    dob: date | None = None
    mrn: str | None = None
    document_date: date | None = None
    facility_name: str | None = None

    def found_fields(self) -> list[str]:
        """Return the names of fields that were successfully extracted."""
        fields = []
        if self.mrn:
            fields.append("mrn")
        if self.patient_first_name:
            fields.append("first_name")
        if self.patient_last_name:
            fields.append("last_name")
        if self.dob:
            fields.append("dob")
        if self.document_date:
            fields.append("document_date")
        if self.facility_name:
            fields.append("facility_name")
        return fields


def parse(text: str) -> ParsedMetadata:
    """Extract patient and document metadata from free-form clinical text."""
    if not text.strip():
        return ParsedMetadata()

    first_name, last_name = _extract_name(text)
    metadata = ParsedMetadata(
        mrn=_extract_mrn(text),
        patient_first_name=first_name,
        patient_last_name=last_name,
        dob=_extract_dob(text),
        document_date=_extract_document_date(text),
        facility_name=_extract_facility(text),
    )

    logger.debug("Parsed metadata fields: %s", metadata.found_fields())
    return metadata


def _extract_mrn(text: str) -> str | None:
    for pattern in _MRN_PATTERNS:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return None


def _extract_name(text: str) -> tuple[str | None, str | None]:
    for pattern, order in _NAME_PATTERNS:
        m = re.search(pattern, text)
        if m:
            g1, g2 = m.group(1).strip(), m.group(2).strip()
            return (g1, g2) if order == "first_last" else (g2, g1)
    return None, None


def _extract_dob(text: str) -> date | None:
    for pattern in _DOB_PATTERNS:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            parsed = _parse_date(m.group(1))
            if parsed:
                return parsed
    return None


def _extract_document_date(text: str) -> date | None:
    for pattern in _DOCUMENT_DATE_PATTERNS:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            parsed = _parse_date(m.group(1))
            if parsed:
                return parsed
    return None


def _extract_facility(text: str) -> str | None:
    for pattern in _FACILITY_PATTERNS + _PROVIDER_PATTERNS:
        m = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if m:
            value = m.group(1).strip().rstrip(",.:;")
            if len(value) > 3:
                return value
    return None


def _parse_date(raw: str) -> date | None:
    raw = raw.strip().rstrip(".")
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None
