"""
db_service.py
Handles all employee/candidate data operations.
Analytics Avenue LLP
"""

import json
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "../database/employees.json")

# ─── Role → Default Responsibilities Mapping ─────────────────
ROLE_RESPONSIBILITIES = {
    "Data Analytics Trainee": [
        "Data collection, cleaning, and preprocessing",
        "Building reports and dashboards using Power BI / Excel",
        "End-to-end business development activities",
        "Client engagement and lead generation",
        "Completion of mandatory technical and professional training programs",
    ],
    "Business Analyst": [
        "Requirement gathering and business process analysis",
        "Preparation of BRD, FRD, and project documentation",
        "Coordination between technical and business teams",
        "Data analysis and reporting for stakeholders",
        "Follow-ups and achievement of assigned targets",
    ],
    "Data Analyst": [
        "Data analysis and visualization using Python, SQL, and Power BI",
        "Building and maintaining analytical dashboards",
        "Generating insights from large datasets",
        "Preparing analytical reports for management",
        "Collaborating with cross-functional teams on data projects",
    ],
    "Software Developer": [
        "Designing, developing, and maintaining software applications",
        "Writing clean, scalable, and well-documented code",
        "Participating in code reviews and technical discussions",
        "Debugging and resolving software defects",
        "Collaborating with product and design teams",
    ],
    "HR Executive": [
        "End-to-end recruitment and talent acquisition",
        "Onboarding and induction of new employees",
        "Maintaining employee records and HR documentation",
        "Coordinating performance management activities",
        "Handling employee queries and HR operations",
    ],
    "Talent Acquisition Intern": [
        "Candidate sourcing and screening coordination",
        "Interview scheduling and recruitment follow-ups",
        "HR support activities and documentation",
        "Talent Acquisition process management",
        "Maintaining recruitment trackers and databases",
    ],
    "Data Analytics Intern": [
        "Data cleaning and preprocessing using Python and SQL",
        "Building dashboards and visualizations using Power BI",
        "Working on real-time project-based analytical tasks",
        "Generating business insights from datasets",
        "Preparing reports and presentations for the team",
    ],
    "Marketing Intern": [
        "Supporting digital marketing campaigns and content creation",
        "Social media management and engagement tracking",
        "Market research and competitor analysis",
        "Lead generation and follow-up coordination",
        "Preparing marketing reports and analytics",
    ],
    "Business Development Intern": [
        "End-to-end business development activities",
        "Client engagement and lead generation",
        "Follow-ups and achievement of assigned targets",
        "Preparation of reports and dashboards",
        "Completion of mandatory technical and professional training programs",
    ],
}


def get_responsibilities_for_role(role: str) -> list:
    """Return default responsibilities for a given role."""
    return ROLE_RESPONSIBILITIES.get(role, [])


# ─── DB Load/Save ─────────────────────────────────────────────

def load_db() -> dict:
    with open(DB_PATH, "r") as f:
        return json.load(f)


def save_db(data: dict):
    with open(DB_PATH, "w") as f:
        json.dump(data, f, indent=2)


# ─── Candidates ───────────────────────────────────────────────

def get_all_candidates() -> list:
    return load_db().get("candidates", [])


def get_candidate_names() -> list:
    return [c["name"] for c in get_all_candidates()]


def get_candidate_by_name(name: str) -> dict:
    for c in get_all_candidates():
        if c["name"].lower() == name.lower():
            return c
    return {}


def add_candidate(candidate: dict):
    db = load_db()
    existing_ids = [c["id"] for c in db["candidates"]]
    candidate["id"] = max(existing_ids) + 1 if existing_ids else 1
    db["candidates"].append(candidate)
    save_db(db)


# ─── Interns ──────────────────────────────────────────────────

def get_all_interns() -> list:
    return load_db().get("interns", [])


def get_intern_names() -> list:
    return [i["name"] for i in get_all_interns()]


def get_intern_by_name(name: str) -> dict:
    for i in get_all_interns():
        if i["name"].lower() == name.lower():
            return i
    return {}


def add_intern(intern: dict):
    db = load_db()
    existing_ids = [i["id"] for i in db["interns"]]
    intern["id"] = max(existing_ids) + 1 if existing_ids else 1
    db["interns"].append(intern)
    save_db(db)


# ─── Roles & Departments ──────────────────────────────────────

def get_roles() -> list:
    return load_db().get("roles", [])


def get_departments() -> list:
    return load_db().get("departments", [])


# ─── Document History ─────────────────────────────────────────

HISTORY_PATH = os.path.join(os.path.dirname(__file__), "../output/history.json")


def load_history() -> list:
    if not os.path.exists(HISTORY_PATH):
        return []
    with open(HISTORY_PATH, "r") as f:
        return json.load(f)


def add_to_history(record: dict):
    history = load_history()
    record["generated_at"] = datetime.now().strftime("%d-%m-%Y %H:%M")
    history.insert(0, record)
    history = history[:100]
    os.makedirs(os.path.dirname(HISTORY_PATH), exist_ok=True)
    with open(HISTORY_PATH, "w") as f:
        json.dump(history, f, indent=2)