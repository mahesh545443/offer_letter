"""
internship.py
Handles Internship Completion Letter generation logic.
Analytics Avenue LLP
"""

from datetime import datetime
from modules.pdf_generator import generate_document
from modules.db_service import add_to_history


TEMPLATE_NAME = "internship_template.docx"


def build_context(intern_name: str, salutation: str, reg_no: str,
                   college: str, department: str, role: str,
                   start_date: str, end_date: str, duration: str,
                   responsibilities: list, letter_date: str = None) -> dict:
    """
    Build the context dictionary for the internship template.

    Placeholders used in internship_template.docx:
      {{ salutation }}          → Ms. / Mr.
      {{ intern_name }}         → Full name
      {{ reg_no }}              → Registration number
      {{ college }}             → College / Institution
      {{ department }}          → Department
      {{ role }}                → Internship role
      {{ start_date }}          → Internship start date
      {{ end_date }}            → Internship end date
      {{ duration }}            → e.g. "one month", "three months"
      {{ responsibilities }}    → List of responsibilities (use Jinja2 loop in template)
      {{ letter_date }}         → Date of the letter
    """
    if not letter_date:
        letter_date = datetime.now().strftime("%d-%m-%Y")

    return {
        "salutation": salutation,
        "intern_name": intern_name,
        "reg_no": reg_no,
        "college": college,
        "department": department,
        "role": role,
        "start_date": start_date,
        "end_date": end_date,
        "duration": duration,
        "responsibilities": responsibilities,
        "letter_date": letter_date,
    }


def generate_internship(intern_name: str, salutation: str, reg_no: str,
                         college: str, department: str, role: str,
                         start_date: str, end_date: str, duration: str,
                         responsibilities: list, letter_date: str = None) -> dict:
    """
    Generate Internship Completion Letter.

    Returns:
        dict with docx_path, pdf_path, filename, success, error
    """
    context = build_context(intern_name, salutation, reg_no, college,
                             department, role, start_date, end_date,
                             duration, responsibilities, letter_date)

    result = generate_document(
        template_name=TEMPLATE_NAME,
        context=context,
        candidate_name=intern_name,
        doc_type="Internship"
    )

    if result["success"]:
        add_to_history({
            "type": "Internship Completion Letter",
            "candidate_name": intern_name,
            "role": role,
            "duration": duration,
            "filename": result["filename"],
            "docx_path": result["docx_path"],
            "pdf_path": result["pdf_path"],
        })

    return result
