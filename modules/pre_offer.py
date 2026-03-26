"""
pre_offer.py
Handles Pre-Offer Letter generation logic.
Analytics Avenue LLP
"""

from datetime import datetime
from modules.pdf_generator import generate_document
from modules.db_service import add_to_history


TEMPLATE_NAME = "pre_offer_template.docx"


def build_context(candidate_name: str, salutation: str, role: str,
                   joining_date: str, letter_date: str = None,
                   stipend: str = "₹10,000", incentive: str = "₹15,000") -> dict:
    """
    Build the context dictionary for the pre-offer template.

    Placeholders used in pre_offer_template.docx:
      {{ salutation }}         → Ms. / Mr.
      {{ candidate_name }}     → Full name
      {{ role }}               → Job role/position
      {{ joining_date }}       → Date of joining
      {{ letter_date }}        → Date of the letter
      {{ stipend }}            → Fixed stipend amount e.g. ₹10,000
      {{ incentive }}          → Performance incentive amount e.g. ₹15,000
    """
    if not letter_date:
        letter_date = datetime.now().strftime("%d-%m-%Y")

    return {
        "salutation": salutation,
        "candidate_name": candidate_name,
        "role": role,
        "joining_date": joining_date,
        "letter_date": letter_date,
        "stipend": stipend,
        "incentive": incentive,
    }


def generate_pre_offer(candidate_name: str, salutation: str, role: str,
                        joining_date: str, letter_date: str = None,
                        stipend: str = "₹10,000", incentive: str = "₹15,000") -> dict:
    """
    Generate Pre-Offer Letter for a candidate.

    Returns:
        dict with docx_path, pdf_path, filename, success, error
    """
    context = build_context(candidate_name, salutation, role,
                             joining_date, letter_date, stipend, incentive)

    result = generate_document(
        template_name=TEMPLATE_NAME,
        context=context,
        candidate_name=candidate_name,
        doc_type="PreOffer"
    )

    # Save to history
    if result["success"]:
        add_to_history({
            "type": "Pre-Offer Letter",
            "candidate_name": candidate_name,
            "role": role,
            "joining_date": joining_date,
            "filename": result["filename"],
            "docx_path": result["docx_path"],
            "pdf_path": result["pdf_path"],
        })

    return result