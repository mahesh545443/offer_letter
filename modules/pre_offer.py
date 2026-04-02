"""
pre_offer.py
Analytics Avenue LLP — Pre-Offer Letter Generator
"""

import os
from datetime import datetime
from modules.pdf_generator import generate_document, generate_pdf_direct
from modules.db_service import add_to_history

TEMPLATE_NAME = "pre_offer_template.docx"
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "../output")


def generate_pre_offer(
    candidate_name: str,
    salutation: str,
    role: str,
    joining_date: str,
    letter_date: str = None,
    stipend: str = "\u20b910,000",
    incentive: str = "",
    ctc_range: str = "\u20b94 LPA to \u20b96 LPA",
    training_period: str = None,
    probation_start: str = None,
    probation_dur: str = "two to four months",
    has_probation: bool = True,
    custom_rr: list = None,
) -> dict:
    """Generate Pre-Offer Letter PDF and DOCX."""

    if not letter_date:
        letter_date = datetime.now().strftime("%d-%m-%Y")

    context = {
        "salutation":      salutation,
        "candidate_name":  candidate_name,
        "role":            role,
        "joining_date":    joining_date,
        "letter_date":     letter_date,
        "stipend":         stipend,
        "incentive":       incentive,        # empty = hide incentive section
        "ctc_range":       ctc_range,
        "training_period": training_period,
        "probation_start": probation_start,
        "probation_dur":   probation_dur,
        "has_probation":   has_probation,
        "custom_rr":       custom_rr or [],
    }

    result = generate_document(
        template_name=TEMPLATE_NAME,
        context=context,
        candidate_name=candidate_name,
        doc_type="PreOffer",
    )

    if result["success"]:
        add_to_history({
            "type":           "Pre-Offer Letter",
            "candidate_name": candidate_name,
            "role":           role,
            "joining_date":   joining_date,
            "filename":       result["filename"],
            "docx_path":      result["docx_path"],
            "pdf_path":       result["pdf_path"],
        })

    return result
