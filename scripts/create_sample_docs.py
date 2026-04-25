#!/usr/bin/env python3
"""
Generate synthetic sample PDFs in sample_docs/ for manual testing.

Run once after cloning:
    python scripts/create_sample_docs.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fpdf import FPDF, XPos, YPos

OUTPUT_DIR = Path(__file__).parent.parent / "sample_docs"


def _make_pdf(title: str, lines: list[str]) -> FPDF:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, text=title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", size=11)
    pdf.ln(4)
    for line in lines:
        pdf.cell(0, 7, text=line, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    return pdf


def create_lab_result() -> None:
    doc = _make_pdf(
        title="LABORATORY REPORT",
        lines=[
            "Patient: Dorothy Nguyen",
            "MRN: MRN-10002",
            "Date of Birth: 07/22/1955",
            "Collection Date: 04/10/2026",
            "Ordering Provider: Dr. Ramona Esteves",
            "Facility: Westlake Medical Group",
            "",
            "TEST RESULTS",
            "Hemoglobin A1c:       6.8%        Reference: <5.7%",
            "Fasting Glucose:      118 mg/dL   Reference: 70-99 mg/dL",
            "Total Cholesterol:    204 mg/dL   Reference: <200 mg/dL",
            "HDL:                   52 mg/dL   Reference: >40 mg/dL",
            "LDL:                  131 mg/dL   Reference: <100 mg/dL",
            "Triglycerides:        105 mg/dL   Reference: <150 mg/dL",
            "",
            "Results reviewed by: Dr. Ramona Esteves, MD",
        ],
    )
    doc.output(str(OUTPUT_DIR / "lab_result.pdf"))
    print("Created: lab_result.pdf")


def create_discharge_summary() -> None:
    doc = _make_pdf(
        title="DISCHARGE SUMMARY",
        lines=[
            "Patient: Robert Castillo",
            "MRN: MRN-10003",
            "Date of Birth: 11/05/1962",
            "Admission Date: 04/05/2026",
            "Discharge Date: 04/09/2026",
            "Discharging Provider: Dr. Samuel Osei",
            "Facility: Northbrook Regional Hospital",
            "",
            "PRINCIPAL DIAGNOSIS",
            "Community-acquired pneumonia, right lower lobe",
            "",
            "HOSPITAL COURSE",
            "Patient presented with 3-day history of productive cough, fever to 38.9C,",
            "and dyspnea. CXR confirmed right lower lobe infiltrate. Treated with IV",
            "ceftriaxone and azithromycin with good clinical response. Afebrile x48h.",
            "",
            "DISCHARGE MEDICATIONS",
            "Amoxicillin-clavulanate 875mg PO BID x 5 days",
            "Guaifenesin 400mg PO q4h PRN",
            "",
            "FOLLOW-UP",
            "Return to clinic in 7-10 days or sooner if symptoms worsen.",
        ],
    )
    doc.output(str(OUTPUT_DIR / "discharge_summary.pdf"))
    print("Created: discharge_summary.pdf")


def create_referral() -> None:
    doc = _make_pdf(
        title="REFERRAL REQUEST",
        lines=[
            "Referring Provider: Dr. Angela Park, MD",
            "Patient: Thomas Bergmann",
            "MRN: MRN-10005",
            "Date of Birth: 09/18/1957",
            "Date: 04/15/2026",
            "Facility: Sunrise Family Medicine",
            "",
            "Referred To: Cardiology - Dr. Marcus Webb",
            "",
            "REASON FOR REFERRAL",
            "Patient presents with exertional chest discomfort x6 weeks and new-onset",
            "dyspnea on moderate exertion. EKG shows nonspecific ST changes. Risk factors",
            "include HTN, hyperlipidemia, and 20 pack-year smoking history.",
            "",
            "Please evaluate for possible coronary artery disease.",
            "",
            "Recent Labs: BMP wnl, Troponin x2 negative, BNP 88 pg/mL",
            "Current Medications: Lisinopril 10mg, Atorvastatin 40mg",
        ],
    )
    doc.output(str(OUTPUT_DIR / "referral.pdf"))
    print("Created: referral.pdf")


def create_imaging_report() -> None:
    doc = _make_pdf(
        title="RADIOLOGY REPORT",
        lines=[
            "Patient: Helen Kowalski",
            "MRN: MRN-10006",
            "Date of Birth: 06/03/1944",
            "Study Date: 04/12/2026",
            "Ordering Provider: Dr. Priya Nair",
            "Facility: Eastside Imaging Center",
            "",
            "EXAMINATION: MRI Brain without contrast",
            "",
            "CLINICAL INDICATION: Memory complaints, rule out vascular dementia.",
            "",
            "FINDINGS",
            "Brain parenchyma: Mild diffuse cortical atrophy, age-appropriate.",
            "White matter: Scattered periventricular T2/FLAIR hyperintensities, Fazekas",
            "grade 1, consistent with mild small vessel ischemic disease.",
            "Ventricles: Mildly prominent, symmetric.",
            "No acute infarct, hemorrhage, or mass effect identified.",
            "",
            "IMPRESSION",
            "1. Mild small vessel ischemic disease.",
            "2. Mild age-appropriate cortical atrophy.",
            "3. No acute intracranial pathology.",
            "",
            "Interpreting Radiologist: Dr. Yolanda Serrano, MD",
        ],
    )
    doc.output(str(OUTPUT_DIR / "imaging_report.pdf"))
    print("Created: imaging_report.pdf")


def create_medication_update() -> None:
    doc = _make_pdf(
        title="MEDICATION RECONCILIATION",
        lines=[
            "Patient: George Tanaka",
            "MRN: MRN-10009",
            "Date of Birth: 08/15/1965",
            "Date: 04/18/2026",
            "Provider: Dr. Fatima Al-Hassan",
            "Facility: Hillcrest Primary Care",
            "",
            "MEDICATION UPDATE",
            "The following changes were made at today's visit:",
            "",
            "DISCONTINUED",
            "Metformin 500mg PO BID - discontinued due to GI intolerance",
            "",
            "NEW PRESCRIPTIONS",
            "Semaglutide 0.5mg SQ weekly - start 04/20/2026",
            "Pantoprazole 40mg PO daily - for GI symptoms",
            "",
            "CONTINUED WITHOUT CHANGE",
            "Amlodipine 5mg PO daily",
            "Rosuvastatin 20mg PO nightly",
            "Aspirin 81mg PO daily",
            "",
            "Patient counseled on new medication administration and side effects.",
        ],
    )
    doc.output(str(OUTPUT_DIR / "medication_update.pdf"))
    print("Created: medication_update.pdf")


def create_administrative() -> None:
    doc = _make_pdf(
        title="PRIOR AUTHORIZATION REQUEST",
        lines=[
            "Date: 04/16/2026",
            "Patient: Barbara Ellison",
            "MRN: MRN-10010",
            "Date of Birth: 02/21/1958",
            "Insurance: Meridian Health Plan  Member ID: MHP-887234",
            "Requesting Provider: Dr. Leonard Cross, MD",
            "Facility: Lakewood Specialty Clinic",
            "",
            "REQUESTED SERVICE",
            "CPT Code: 70553 - MRI Brain with and without contrast",
            "Diagnosis: G35 - Multiple Sclerosis",
            "",
            "CLINICAL JUSTIFICATION",
            "Patient with established MS diagnosis presents with new symptoms of left",
            "upper extremity weakness x2 weeks. Neurologist requesting MRI to evaluate",
            "for new demyelinating lesion and assess treatment response.",
            "",
            "Supporting documentation attached: clinic note 04/15/2026",
        ],
    )
    doc.output(str(OUTPUT_DIR / "administrative.pdf"))
    print("Created: administrative.pdf")


def main() -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    create_lab_result()
    create_discharge_summary()
    create_referral()
    create_imaging_report()
    create_medication_update()
    create_administrative()
    print(f"\nSample documents written to {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
