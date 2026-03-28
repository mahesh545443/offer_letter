"""
app.py
Analytics Avenue LLP — HR Letter Generator
Streamlit UI — Professional Theme
"""

import os
import sys
import streamlit as st
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta

sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from modules.db_service import (
    get_candidate_names, get_intern_names,
    get_candidate_by_name, get_intern_by_name,
    get_roles, get_departments,
    add_candidate, add_intern, load_history,
    get_responsibilities_for_role
)
from modules.ai_service import parse_prompt, parse_salary_prompt_groq
from modules.salary_calc import calculate_salary_breakup, format_inr
from modules.pre_offer import generate_pre_offer
from modules.internship import generate_internship
from modules.offer_letter import generate_offer_letter
from modules.pdf_generator import read_file_bytes

# ─── Page Config ──────────────────────────────────────────────
st.set_page_config(
    page_title="HR Letter Generator — Analytics Avenue",
    page_icon="assets/letterhead_final.png",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Professional CSS ─────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    background-color: #f0f4f8;
}

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    background: #ffffff;
    border-right: 1px solid #dbe3ed;
}
section[data-testid="stSidebar"] * {
    color: #1a2942 !important;
}

/* ── Top bar ── */
.aa-topbar {
    background: #ffffff;
    border-bottom: 2px solid #1a56b0;
    padding: 14px 28px;
    display: flex;
    align-items: center;
    gap: 16px;
    margin-bottom: 20px;
    border-radius: 0 0 8px 8px;
    box-shadow: 0 2px 8px rgba(26,86,176,0.08);
}
.aa-topbar-name {
    font-size: 20px;
    font-weight: 700;
    color: #064b86;
    letter-spacing: -0.3px;
}
.aa-topbar-sub {
    font-size: 12px;
    color: #7a8fa6;
    margin-top: 1px;
}

/* ── Page title ── */
.aa-page-title {
    font-size: 22px;
    font-weight: 700;
    color: #0d2b5e;
    margin-bottom: 2px;
}
.aa-page-sub {
    font-size: 13px;
    color: #6b7c93;
    margin-bottom: 20px;
}

/* ── Cards ── */
.aa-card {
    background: #ffffff;
    border: 1px solid #dbe3ed;
    border-radius: 10px;
    padding: 22px 24px;
    margin-bottom: 16px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04);
}
.aa-card-title {
    font-size: 13px;
    font-weight: 600;
    color: #1a56b0;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    margin-bottom: 14px;
    padding-bottom: 8px;
    border-bottom: 1px solid #e8eef6;
}

/* ── Salary preview table ── */
.sal-table { width: 100%; border-collapse: collapse; margin-top: 8px; }
.sal-table tr { border-bottom: 1px solid #e8eef6; }
.sal-table tr:last-child { border-bottom: none; font-weight: 600; color: #0d2b5e; }
.sal-table td { padding: 7px 4px; font-size: 13px; color: #2d3748; }
.sal-table td:last-child { text-align: right; font-weight: 500; color: #1a56b0; }
.sal-table tr.gross td { background: #f0f5ff; font-weight: 600; }
.sal-table tr.ctc td { background: #e8f0fe; font-weight: 700; color: #0d2b5e; }

/* ── Tabs ── */
div[data-testid="stTabs"] {
    background: #ffffff;
    border-radius: 10px;
    border: 1px solid #dbe3ed;
    padding: 0;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04);
}
div[data-testid="stTabs"] > div:first-child {
    background: #f5f8ff;
    border-bottom: 2px solid #dbe3ed;
    border-radius: 10px 10px 0 0;
    padding: 0 16px;
}
div[data-testid="stTabs"] button {
    font-size: 13px;
    font-weight: 500;
    color: #6b7c93;
    padding: 12px 20px;
    border: none;
    background: transparent;
}
div[data-testid="stTabs"] button[aria-selected="true"] {
    color: #1a56b0;
    border-bottom: 2px solid #1a56b0;
    font-weight: 600;
}
div[data-testid="stTabs"] > div:last-child {
    padding: 24px;
}

/* ── Buttons ── */
.stButton > button {
    background: #1a56b0;
    color: white !important;
    border: none;
    border-radius: 7px;
    font-weight: 600;
    font-size: 13px;
    padding: 10px 20px;
    width: 100%;
    letter-spacing: 0.2px;
    transition: background 0.2s;
}
.stButton > button:hover {
    background: #1344a0 !important;
    color: white !important;
}
.stDownloadButton > button {
    background: #f0f5ff;
    color: #1a56b0 !important;
    border: 1px solid #1a56b0;
    border-radius: 7px;
    font-weight: 600;
    font-size: 13px;
    width: 100%;
}
.stDownloadButton > button:hover {
    background: #e0ecff !important;
}

/* ── Form labels ── */
.stSelectbox label, .stTextInput label,
.stDateInput label, .stTextArea label {
    font-weight: 600;
    font-size: 12px;
    color: #4a5568;
    text-transform: uppercase;
    letter-spacing: 0.4px;
}

/* ── Section label ── */
.field-group-label {
    font-size: 12px;
    font-weight: 700;
    color: #1a56b0;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin: 16px 0 10px;
    padding-left: 2px;
}

/* ── Info / success / error ── */
.aa-info {
    background: #f0f5ff;
    border-left: 3px solid #1a56b0;
    border-radius: 6px;
    padding: 10px 14px;
    font-size: 13px;
    color: #1a2942;
    margin: 8px 0;
}
.aa-success {
    background: #f0fdf4;
    border-left: 3px solid #22c55e;
    border-radius: 6px;
    padding: 10px 14px;
    font-size: 13px;
    color: #166534;
    margin: 8px 0;
}
.aa-error {
    background: #fff5f5;
    border-left: 3px solid #ef4444;
    border-radius: 6px;
    padding: 10px 14px;
    font-size: 13px;
    color: #991b1b;
    margin: 8px 0;
}

/* ── History cards ── */
.hist-card {
    background: #f8faff;
    border: 1px solid #dbe3ed;
    border-radius: 8px;
    padding: 12px 16px;
    margin-bottom: 8px;
}

/* ── Divider ── */
.aa-divider {
    border: none;
    border-top: 1px solid #e2e8f0;
    margin: 16px 0;
}

/* ── Parsed params box ── */
.parsed-box {
    background: #f5f8ff;
    border: 1px solid #c3d4f0;
    border-radius: 7px;
    padding: 10px 14px;
    font-size: 12px;
    color: #2d3748;
    margin: 8px 0 12px;
    line-height: 1.8;
}
.parsed-box span { font-weight: 600; color: #1a56b0; }

/* ── Duration badge ── */
.dur-badge {
    background: #e8f0fe;
    color: #1a56b0;
    border-radius: 20px;
    padding: 3px 12px;
    font-size: 12px;
    font-weight: 600;
    display: inline-block;
    margin: 6px 0;
}
</style>
""", unsafe_allow_html=True)

# ─── Top Bar ──────────────────────────────────────────────────
logo_url = "https://raw.githubusercontent.com/Analytics-Avenue/streamlit-dataapp/main/logo.png"
st.markdown(f"""
<div class="aa-topbar">
    <img src="{logo_url}" width="48" style="border-radius:6px; border:1px solid #dbe3ed;">
    <div>
        <div class="aa-topbar-name">Analytics Avenue LLP</div>
        <div class="aa-topbar-sub">Empower your business with data-driven insights</div>
    </div>
    <div style="flex:1;"></div>
    <div style="font-size:12px; color:#7a8fa6;">HR Automation Platform</div>
</div>
""", unsafe_allow_html=True)

# ─── Sidebar ──────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:20px;">
        <img src="{logo_url}" width="36" style="border-radius:4px;border:1px solid #dbe3ed;">
        <div>
            <div style="font-size:13px;font-weight:700;color:#064b86;">Analytics Avenue LLP</div>
            <div style="font-size:11px;color:#7a8fa6;">HR Automation</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()
    st.markdown("**Add New Person**")
    person_type = st.radio("Type", ["Candidate", "Intern"], horizontal=True, label_visibility="collapsed")

    with st.expander("Add to Database", expanded=False):
        if person_type == "Candidate":
            new_name  = st.text_input("Full Name *", key="sb_cname")
            new_sal   = st.selectbox("Salutation *", ["Ms.", "Mr.", "Dr."], key="sb_csal")
            new_role  = st.selectbox("Role *", get_roles(), key="sb_crole")
            new_dept  = st.selectbox("Department *", get_departments(), key="sb_cdept")
            new_join  = st.date_input("Joining Date *", key="sb_cjoin")
            new_email = st.text_input("Email", key="sb_cemail")
            if st.button("Add Candidate", key="sb_addcand"):
                if new_name:
                    add_candidate({"name": new_name, "salutation": new_sal, "role": new_role,
                                   "department": new_dept, "joining_date": new_join.strftime("%d-%m-%Y"),
                                   "email": new_email, "phone": ""})
                    st.success(f"{new_name} added.")
                    st.rerun()
        else:
            new_name    = st.text_input("Full Name *", key="sb_iname")
            new_sal     = st.selectbox("Salutation *", ["Ms.", "Mr.", "Dr."], key="sb_isal")
            new_reg     = st.text_input("Reg. No.", key="sb_ireg")
            new_college = st.text_input("College / Institution", key="sb_icollege")
            new_dept    = st.selectbox("Department *", get_departments(), key="sb_idept")
            new_role    = st.selectbox("Role *", get_roles(), key="sb_irole")
            new_start   = st.date_input("Start Date *", key="sb_istart")
            new_end     = st.date_input("End Date *", key="sb_iend")
            new_email   = st.text_input("Email", key="sb_iemail")
            if st.button("Add Intern", key="sb_addintern"):
                if new_name:
                    add_intern({"name": new_name, "salutation": new_sal, "reg_no": new_reg,
                                "college": new_college, "department": new_dept, "role": new_role,
                                "start_date": new_start.strftime("%d-%m-%Y"),
                                "end_date": new_end.strftime("%d-%m-%Y"),
                                "duration": "", "responsibilities": [], "email": new_email})
                    st.success(f"{new_name} added.")
                    st.rerun()

    st.divider()
    st.markdown("**Settings**")
    groq_model = st.selectbox("Groq Model", [
        "llama3-8b-8192", "llama3-70b-8192", "mixtral-8x7b-32768", "gemma2-9b-it"
    ], label_visibility="visible", key="groq_model_select")
    st.divider()
    st.caption("Analytics Avenue LLP · HR Automation · v2.0")


# ─── Tabs ─────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "Pre-Offer Letter",
    "Offer Letter",
    "Internship Certificate",
    "History"
])


# ══════════════════════════════════════════════
# TAB 1 — PRE-OFFER LETTER
# ══════════════════════════════════════════════
with tab1:
    st.markdown('<div class="aa-page-title">Pre-Offer Letter</div>', unsafe_allow_html=True)
    st.markdown('<div class="aa-page-sub">Generate a pre-offer letter with probation terms and compensation details.</div>', unsafe_allow_html=True)

    col1, col2 = st.columns([1, 1], gap="large")

    with col1:
        st.markdown('<div class="field-group-label">Candidate Details</div>', unsafe_allow_html=True)
        pre_name_typed = st.text_input("Full Name", placeholder="Enter candidate full name", key="pre_name_manual")
        col_a, col_b = st.columns(2)
        with col_a:
            salutation_pre = st.selectbox("Salutation", ["Ms.", "Mr.", "Dr."], key="pre_sal")
        with col_b:
            role_pre = st.selectbox("Role / Designation", get_roles(), key="pre_role")

        joining_date_pre = st.date_input("Joining Date", value=date.today(), key="pre_join")
        letter_date_pre  = st.date_input("Letter Date",  value=date.today(), key="pre_letter_date")

        st.markdown('<div class="field-group-label">Probation Compensation</div>', unsafe_allow_html=True)
        col_s, col_i = st.columns(2)
        with col_s:
            stipend_pre = st.selectbox("Fixed Stipend / Base Pay",
                ["₹10,000", "₹12,000", "₹15,000"], key="pre_stipend")
        with col_i:
            incentive_pre = st.selectbox("Performance Incentive (Up to)",
                ["₹15,000", "₹18,000", "₹20,000"], key="pre_incentive")

    with col2:
        st.markdown('<div class="field-group-label">Preview &amp; Generate</div>', unsafe_allow_html=True)
        st.markdown(f"""
        <div class="aa-card">
            <div style="font-size:13px;color:#4a5568;line-height:2;">
                <b>Candidate:</b> {pre_name_typed.strip() or "—"}<br>
                <b>Role:</b> {role_pre}<br>
                <b>Joining:</b> {joining_date_pre.strftime("%d %b %Y")}<br>
                <b>Stipend:</b> {stipend_pre} / month<br>
                <b>Incentive:</b> Up to {incentive_pre} / month
            </div>
        </div>
        """, unsafe_allow_html=True)

        generate_pre = st.button("Generate Pre-Offer Letter", key="gen_pre", use_container_width=True)

        if generate_pre:
            candidate_name = pre_name_typed.strip()
            if not candidate_name:
                st.error("Please enter a candidate name.")
            else:
                with st.spinner("Generating letter..."):
                    result = generate_pre_offer(
                        candidate_name=candidate_name,
                        salutation=salutation_pre,
                        role=role_pre,
                        joining_date=joining_date_pre.strftime("%d-%m-%Y"),
                        letter_date=letter_date_pre.strftime("%d-%m-%Y"),
                        stipend=stipend_pre,
                        incentive=incentive_pre,
                    )
                if result["success"]:
                    if candidate_name not in get_candidate_names():
                        add_candidate({"name": candidate_name, "salutation": salutation_pre,
                                       "role": role_pre, "department": "Analytics",
                                       "joining_date": joining_date_pre.strftime("%d-%m-%Y"),
                                       "email": "", "phone": ""})
                    st.session_state["pre_result"] = result
                else:
                    st.error(f"Error: {result['error']}")

        if st.session_state.get("pre_result"):
            r = st.session_state["pre_result"]
            st.markdown(f'<div class="aa-success">Letter ready: {r["filename"]}</div>', unsafe_allow_html=True)
            col_dl1, col_dl2 = st.columns(2)
            with col_dl1:
                st.download_button("Download DOCX", data=read_file_bytes(r["docx_path"]),
                    file_name=f"{r['filename']}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    key="persist_pre_docx")
            with col_dl2:
                if r.get("pdf_path") and os.path.exists(r["pdf_path"]):
                    st.download_button("Download PDF", data=read_file_bytes(r["pdf_path"]),
                        file_name=f"{r['filename']}.pdf", mime="application/pdf",
                        key="persist_pre_pdf")


# ══════════════════════════════════════════════
# TAB 2 — OFFER LETTER
# ══════════════════════════════════════════════
with tab2:
    st.markdown('<div class="aa-page-title">Offer Letter</div>', unsafe_allow_html=True)
    st.markdown('<div class="aa-page-sub">Generate a full offer letter with salary breakup table.</div>', unsafe_allow_html=True)

    col1, col2 = st.columns([1, 1], gap="large")

    with col1:
        st.markdown('<div class="field-group-label">Candidate Details</div>', unsafe_allow_html=True)
        offer_name_typed = st.text_input("Full Name", placeholder="Enter candidate full name", key="offer_name_manual")
        col_a, col_b = st.columns(2)
        with col_a:
            salutation_offer = st.selectbox("Salutation", ["Ms.", "Mr.", "Dr."], key="offer_sal")
        with col_b:
            role_offer = st.selectbox("Designation", get_roles(), key="offer_role")

        dept_offer         = st.selectbox("Department", get_departments(), key="offer_dept")
        joining_date_offer = st.date_input("Joining Date", value=date.today(), key="offer_join")
        letter_date_offer  = st.date_input("Letter Date",  value=date.today(), key="offer_letter_date")

    with col2:
        st.markdown('<div class="field-group-label">Salary Structure</div>', unsafe_allow_html=True)
        salary_prompt = st.text_area(
            "Salary Prompt",
            placeholder='e.g. "6 LPA, 40% basic, no PF, 10% variable"\n"5 LPA, basic 50%, PF 12%, no variable"',
            height=80, key="salary_prompt"
        )

        parse_salary_btn = st.button("Calculate Salary Breakup", key="parse_salary")

        if "salary_params" not in st.session_state:
            st.session_state.salary_params = None
        if "salary_result" not in st.session_state:
            st.session_state.salary_result = None

        if parse_salary_btn and salary_prompt:
            with st.spinner("Parsing salary structure..."):
                # Groq computes actual rupee amounts — no separate calculate call needed
                result = parse_salary_prompt_groq(salary_prompt, model=groq_model)
                st.session_state.salary_params = result
                st.session_state.salary_result = result

        if st.session_state.salary_params:
            p = st.session_state.salary_params
            pf_display = "Not applicable" if p["pf_percent"] == 0 else f"{p['pf_percent']}% of Basic"
            st.markdown(f"""
            <div class="parsed-box">
                <span>CTC:</span> &#8377;{p['ctc_annual']:,.0f} &nbsp;|&nbsp;
                <span>Basic:</span> {p['base_percent']}% of CTC &nbsp;|&nbsp;
                <span>HRA:</span> {p['hra_percent']}% of Basic<br>
                <span>PF:</span> {pf_display} &nbsp;|&nbsp;
                <span>Variable:</span> {p['variable_percent']}% of CTC
            </div>
            """, unsafe_allow_html=True)

        if st.session_state.salary_result:
            s = st.session_state.salary_result
            st.markdown(f"""
            <table class="sal-table">
                <tr><td>Basic Salary</td><td>{s['basic_monthly_str']}/mo</td></tr>
                <tr><td>HRA</td><td>{s['hra_monthly_str']}/mo</td></tr>
                <tr><td>PF — Employer</td><td>{s['pf_monthly_str']}/mo</td></tr>
                <tr><td>Special Allowance</td><td>{s['special_allowance_monthly_str']}/mo</td></tr>
                <tr class="gross"><td><b>Gross Monthly</b></td><td><b>{s['gross_monthly_str']}</b></td></tr>
                <tr><td>Variable Pay (Annual)</td><td>{s['variable_annual_str']}</td></tr>
                <tr class="ctc"><td><b>Total CTC (Annual)</b></td><td><b>{s['ctc_annual_str']}</b></td></tr>
            </table>
            """, unsafe_allow_html=True)

        st.markdown("")
        generate_offer = st.button("Generate Offer Letter", key="gen_offer", use_container_width=True)

        if generate_offer:
            if not offer_name_typed.strip():
                st.error("Please enter a candidate name.")
            elif not st.session_state.salary_result:
                st.error("Please calculate salary breakup first.")
            else:
                p = st.session_state.salary_params
                with st.spinner("Generating offer letter..."):
                    result = generate_offer_letter(
                        candidate_name=offer_name_typed.strip(),
                        salutation=salutation_offer,
                        role=role_offer,
                        department=dept_offer,
                        joining_date=joining_date_offer.strftime("%d-%m-%Y"),
                        ctc_annual=p["ctc_annual"],
                        base_percent=p["base_percent"],
                        hra_percent=p["hra_percent"],
                        pf_percent=p["pf_percent"],
                        variable_percent=p["variable_percent"],
                        letter_date=letter_date_offer.strftime("%d-%m-%Y"),
                    )
                if result["success"]:
                    if offer_name_typed.strip() not in get_candidate_names():
                        add_candidate({"name": offer_name_typed.strip(), "salutation": salutation_offer,
                                       "role": role_offer, "department": dept_offer,
                                       "joining_date": joining_date_offer.strftime("%d-%m-%Y"),
                                       "email": "", "phone": ""})
                    st.session_state["offer_result"] = result
                else:
                    st.error(f"Error: {result['error']}")

        if st.session_state.get("offer_result"):
            r = st.session_state["offer_result"]
            st.markdown(f'<div class="aa-success">Letter ready: {r["filename"]}</div>', unsafe_allow_html=True)
            col_dl1, col_dl2 = st.columns(2)
            with col_dl1:
                st.download_button("Download DOCX", data=read_file_bytes(r["docx_path"]),
                    file_name=f"{r['filename']}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    key="persist_offer_docx")
            with col_dl2:
                if r.get("pdf_path") and os.path.exists(r["pdf_path"]):
                    st.download_button("Download PDF", data=read_file_bytes(r["pdf_path"]),
                        file_name=f"{r['filename']}.pdf", mime="application/pdf",
                        key="persist_offer_pdf")


# ══════════════════════════════════════════════
# TAB 3 — INTERNSHIP CERTIFICATE
# ══════════════════════════════════════════════
with tab3:
    st.markdown('<div class="aa-page-title">Internship Completion Certificate</div>', unsafe_allow_html=True)
    st.markdown('<div class="aa-page-sub">Generate a completion certificate. Responsibilities auto-fill based on selected role.</div>', unsafe_allow_html=True)

    col1, col2 = st.columns([1, 1], gap="large")

    with col1:
        st.markdown('<div class="field-group-label">Intern Details</div>', unsafe_allow_html=True)
        intern_name_typed = st.text_input("Full Name", placeholder="Enter intern full name", key="intern_name_manual")

        col_a, col_b = st.columns(2)
        with col_a:
            salutation_intern = st.selectbox("Salutation", ["Ms.", "Mr.", "Dr."], key="intern_sal")
        with col_b:
            reg_no = st.text_input("Reg. No.", key="intern_reg")

        college   = st.text_input("College / Institution", key="intern_college")

        col_c, col_d = st.columns(2)
        with col_c:
            dept_intern = st.selectbox("Department", get_departments(), key="intern_dept")
        with col_d:
            # Role selectbox — key change triggers responsibilities refresh
            role_intern = st.selectbox("Role", get_roles(), key="intern_role")

    with col2:
        st.markdown('<div class="field-group-label">Internship Period</div>', unsafe_allow_html=True)

        # ── Date mode toggle ──────────────────────────────────
        date_mode = st.radio(
            "Date Entry Mode",
            ["Manual (pick start & end)", "Auto (start + duration)"],
            horizontal=True, key="intern_date_mode"
        )

        if date_mode == "Manual (pick start & end)":
            col_a, col_b = st.columns(2)
            with col_a:
                start_date_intern = st.date_input("Start Date", value=date.today(), key="intern_start_manual")
            with col_b:
                end_date_intern = st.date_input("End Date", value=date.today(), key="intern_end_manual")

            # Auto-compute duration text from dates
            delta = relativedelta(end_date_intern, start_date_intern)
            months = delta.months + delta.years * 12
            days   = delta.days
            if months > 0 and days == 0:
                DURATION_WORDS = {1:"one",2:"two",3:"three",4:"four",5:"five",
                                  6:"six",7:"seven",8:"eight",9:"nine",10:"ten",
                                  11:"eleven",12:"twelve"}
                duration_intern = f"{DURATION_WORDS.get(months, str(months))} month{'s' if months > 1 else ''}"
            elif months > 0:
                duration_intern = f"{months} month{'s' if months > 1 else ''} and {days} day{'s' if days > 1 else ''}"
            elif days > 0:
                duration_intern = f"{days} day{'s' if days > 1 else ''}"
            else:
                duration_intern = "—"
            st.markdown(f'<div class="dur-badge">Duration: {duration_intern}</div>', unsafe_allow_html=True)

        else:
            start_date_intern = st.date_input("Start Date", value=date.today(), key="intern_start_auto")
            duration_months_n = st.selectbox("Duration", [1, 2, 3, 4, 6], key="intern_dur_months",
                                              format_func=lambda x: f"{x} month{'s' if x > 1 else ''}")
            end_date_intern = start_date_intern + relativedelta(months=duration_months_n)

            DURATION_WORDS = {1:"one",2:"two",3:"three",4:"four",5:"five",
                              6:"six",7:"seven",8:"eight",9:"nine",10:"ten"}
            duration_intern = f"{DURATION_WORDS.get(duration_months_n, str(duration_months_n))} month{'s' if duration_months_n > 1 else ''}"
            st.markdown(
                f'<div class="dur-badge">'
                f'End Date: {end_date_intern.strftime("%d %b %Y")} &nbsp;|&nbsp; Duration: {duration_intern}'
                f'</div>', unsafe_allow_html=True)

        letter_date_intern = st.date_input("Letter Date", value=date.today(), key="intern_letter_date")

        # ── Responsibilities — auto-refresh on role change ────
        st.markdown('<div class="field-group-label">Responsibilities</div>', unsafe_allow_html=True)
        st.caption("Auto-filled from selected role — editable")

        # Use role as key suffix so text area resets when role changes
        auto_resp    = get_responsibilities_for_role(role_intern)
        default_resp = "\n".join(auto_resp)

        responsibilities_text = st.text_area(
            "Responsibilities",
            value=default_resp,
            height=140,
            key=f"intern_resp_{role_intern}",   # KEY FIX: changes with role → auto-refreshes
            label_visibility="collapsed"
        )

        st.markdown("")
        generate_intern = st.button("Generate Internship Certificate", key="gen_intern", use_container_width=True)

        if generate_intern:
            intern_name = intern_name_typed.strip()
            if not intern_name:
                st.error("Please enter an intern name.")
            else:
                responsibilities = [r.strip() for r in responsibilities_text.split("\n") if r.strip()]
                with st.spinner("Generating certificate..."):
                    result = generate_internship(
                        intern_name=intern_name,
                        salutation=salutation_intern,
                        reg_no=reg_no,
                        college=college,
                        department=dept_intern,
                        role=role_intern,
                        start_date=start_date_intern.strftime("%d-%m-%Y"),
                        end_date=end_date_intern.strftime("%d-%m-%Y"),
                        duration=duration_intern,
                        responsibilities=responsibilities,
                        letter_date=letter_date_intern.strftime("%d-%m-%Y"),
                    )
                if result["success"]:
                    if intern_name not in get_intern_names():
                        add_intern({"name": intern_name, "salutation": salutation_intern,
                                    "reg_no": reg_no, "college": college,
                                    "department": dept_intern, "role": role_intern,
                                    "start_date": start_date_intern.strftime("%d-%m-%Y"),
                                    "end_date": end_date_intern.strftime("%d-%m-%Y"),
                                    "duration": duration_intern,
                                    "responsibilities": responsibilities, "email": ""})
                    st.session_state["intern_result"] = result
                else:
                    st.error(f"Error: {result['error']}")

        if st.session_state.get("intern_result"):
            r = st.session_state["intern_result"]
            st.markdown(f'<div class="aa-success">Certificate ready: {r["filename"]}</div>', unsafe_allow_html=True)
            col_dl1, col_dl2 = st.columns(2)
            with col_dl1:
                st.download_button("Download DOCX", data=read_file_bytes(r["docx_path"]),
                    file_name=f"{r['filename']}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    key="persist_intern_docx")
            with col_dl2:
                if r.get("pdf_path") and os.path.exists(r["pdf_path"]):
                    st.download_button("Download PDF", data=read_file_bytes(r["pdf_path"]),
                        file_name=f"{r['filename']}.pdf", mime="application/pdf",
                        key="persist_intern_pdf")


# ══════════════════════════════════════════════
# TAB 4 — HISTORY
# ══════════════════════════════════════════════
with tab4:
    st.markdown('<div class="aa-page-title">Document History</div>', unsafe_allow_html=True)
    st.markdown('<div class="aa-page-sub">Last 100 generated documents.</div>', unsafe_allow_html=True)

    history = load_history()
    if not history:
        st.markdown('<div class="aa-info">No documents generated yet.</div>', unsafe_allow_html=True)
    else:
        for i, record in enumerate(history):
            with st.expander(
                f"{record.get('type','—')}  ·  {record.get('candidate_name','—')}  ·  {record.get('generated_at','')}",
                expanded=False
            ):
                c1, c2, c3 = st.columns(3)
                c1.caption(f"**Type:** {record.get('type','—')}")
                c2.caption(f"**Name:** {record.get('candidate_name','—')}")
                c3.caption(f"**Role:** {record.get('role','—')}")
                if record.get("ctc"):
                    st.caption(f"**CTC:** {record.get('ctc')}")
                if record.get("joining_date"):
                    st.caption(f"**Joining Date:** {record.get('joining_date')}")

                dl1, dl2 = st.columns(2)
                if record.get("docx_path") and os.path.exists(record["docx_path"]):
                    with dl1:
                        st.download_button("DOCX", data=read_file_bytes(record["docx_path"]),
                            file_name=f"{record['filename']}.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            key=f"hist_docx_{i}")
                if record.get("pdf_path") and os.path.exists(record["pdf_path"]):
                    with dl2:
                        st.download_button("PDF", data=read_file_bytes(record["pdf_path"]),
                            file_name=f"{record['filename']}.pdf",
                            mime="application/pdf", key=f"hist_pdf_{i}")
