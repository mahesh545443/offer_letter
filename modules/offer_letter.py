"""
offer_letter.py
Handles Offer Letter generation with salary breakup.
Analytics Avenue LLP
"""

from datetime import datetime
from modules.pdf_generator import generate_document
from modules.salary_calc import calculate_salary_breakup
from modules.db_service import add_to_history


TEMPLATE_NAME = "offer_letter_template.docx"


def build_context(candidate_name: str, salutation: str, role: str,
                   department: str, joining_date: str,
                   ctc_annual: float, base_percent: float = 40,
                   hra_percent: float = 20, pf_percent: float = 5.0,
                   pf_opted: bool = None,
                   variable_percent: float = 10,
                   letter_date: str = None,
                   salary_data: dict = None) -> dict:
    """
    Build context for offer letter template.

    Placeholders used in offer_letter_template.docx:
      {{ salutation }}                  → Ms. / Mr.
      {{ candidate_name }}              → Full name
      {{ role }}                        → Designation
      {{ department }}                  → Department
      {{ joining_date }}                → Date of joining
      {{ letter_date }}                 → Letter date
      {{ ctc_lpa }}                     → e.g. "6.0 LPA"
      {{ ctc_annual_str }}              → e.g. "₹6,00,000"
      {{ basic_monthly_str }}           → e.g. "₹20,000"
      {{ hra_monthly_str }}             → e.g. "₹4,000"
      {{ pf_monthly_str }}              → e.g. "₹2,400" or "N/A"
      {{ special_allowance_monthly_str }}
      {{ variable_annual_str }}         → e.g. "₹60,000"
      {{ gross_monthly_str }}           → e.g. "₹38,600"
      {{ pf_opted }}                    → True/False
    """
    if not letter_date:
        letter_date = datetime.now().strftime("%d-%m-%Y")

    # Use pre-computed salary from Groq if available, else calculate
    if salary_data:
        salary = salary_data
    else:
        salary = calculate_salary_breakup(
            ctc_annual=ctc_annual,
            base_percent=base_percent,
            hra_percent=hra_percent,
            pf_percent=pf_percent,
            variable_percent=variable_percent,
        )

    context = {
        "salutation": salutation,
        "candidate_name": candidate_name,
        "role": role,
        "department": department,
        "joining_date": joining_date,
        "letter_date": letter_date,
    }
    context.update(salary)
    return context


def generate_offer_letter(candidate_name: str, salutation: str, role: str,
                           department: str, joining_date: str,
                           ctc_annual: float, base_percent: float = 40,
                           hra_percent: float = 20, pf_percent: float = 5.0,
                           pf_opted: bool = None,
                           variable_percent: float = 10,
                           letter_date: str = None,
                           custom_rr: list = None,
                           salary_data: dict = None) -> dict:
    """
    Generate Offer Letter with salary breakup.

    Returns:
        dict with docx_path, pdf_path, filename, success, error
    """
    context = build_context(
        candidate_name, salutation, role, department, joining_date,
        ctc_annual, base_percent, hra_percent, pf_percent,
        pf_opted, variable_percent, letter_date,
        salary_data=salary_data
    )
    if custom_rr:
        context["custom_rr"] = custom_rr

    result = generate_document(
        template_name=TEMPLATE_NAME,
        context=context,
        candidate_name=candidate_name,
        doc_type="OfferLetter"
    )

    if result["success"]:
        add_to_history({
            "type": "Offer Letter",
            "candidate_name": candidate_name,
            "role": role,
            "ctc": context["ctc_lpa"],
            "joining_date": joining_date,
            "filename": result["filename"],
            "docx_path": result["docx_path"],
            "pdf_path": result["pdf_path"],
        })

    return result
