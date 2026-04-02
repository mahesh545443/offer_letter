"""
app.py
Analytics Avenue LLP — HR Letter Generator
"""

import os
import sys
import re
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
from modules.ai_service import (
    fix_role_name, fix_responsibility_line,
    complete_responsibilities, ROLE_DEFAULTS
)

# ─── Page Config ──────────────────────────────────────────────
st.set_page_config(
    page_title="HR Letter Generator — Analytics Avenue",
    page_icon="assets/letterhead_final.png",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─── Helpers ──────────────────────────────────────────────────
def format_amount(raw: str) -> str:
    raw = raw.strip().replace("₹", "").replace(",", "").replace(" ", "")
    try:
        amount = int(float(raw))
        if amount <= 0:
            return ""
        s = str(amount)
        if len(s) <= 3:
            return f"₹{s}"
        last3 = s[-3:]; rest = s[:-3]; parts = []
        while len(rest) > 2:
            parts.append(rest[-2:]); rest = rest[:-2]
        if rest: parts.append(rest)
        parts.reverse()
        return f"₹{','.join(parts)},{last3}"
    except Exception:
        return ""

# ─── Constants ────────────────────────────────────────────────
COLLEGE_DEPARTMENTS = [
    "Computer Science and Engineering",
    "Data Science",
    "Artificial Intelligence",
    "Artificial Intelligence and Machine Learning",
    "Information Technology",
    "Electronics and Communication Engineering",
    "Electrical Engineering",
    "Mechanical Engineering",
    "Civil Engineering",
    "Chemical Engineering",
    "Biotechnology",
    "Business Administration (BBA)",
    "Commerce (B.Com)",
    "MBA",
    "Mathematics",
    "Physics",
    "Psychology",
    "English Literature",
    "Economics",
    "Other",
]

PRESET_ROLES = [
    "Data Analytics Trainee",
    "Data Analyst",
    "Business Analyst",
    "Software Developer",
    "HR Executive",
    "Talent Acquisition Intern",
    "Data Analytics Intern",
    "Marketing Intern",
    "Business Development Intern",
    "Other",
]

CTC_RANGES = [
    "₹2 LPA – ₹3 LPA",
    "₹3 LPA – ₹5 LPA",
    "₹4 LPA – ₹6 LPA",
    "₹5 LPA – ₹8 LPA",
    "₹8 LPA – ₹10 LPA",
    "Other (Custom Range)",
]

# ─── CSS ──────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #f0f4f8; }
[data-testid="collapsedControl"] { display: none; }
section[data-testid="stSidebar"] { display: none; }
.aa-topbar { background:#fff; border-bottom:2px solid #1a56b0; padding:14px 28px; display:flex; align-items:center; gap:16px; margin-bottom:20px; border-radius:0 0 8px 8px; box-shadow:0 2px 8px rgba(26,86,176,0.08); }
.aa-topbar-name { font-size:20px; font-weight:700; color:#064b86; }
.aa-topbar-sub  { font-size:12px; color:#7a8fa6; margin-top:1px; }
.aa-page-title  { font-size:22px; font-weight:700; color:#0d2b5e; margin-bottom:2px; }
.aa-page-sub    { font-size:13px; color:#6b7c93; margin-bottom:20px; }
.aa-card { background:#fff; border:1px solid #dbe3ed; border-radius:10px; padding:22px 24px; margin-bottom:16px; box-shadow:0 1px 4px rgba(0,0,0,0.04); }
.sal-table { width:100%; border-collapse:collapse; margin-top:8px; }
.sal-table tr { border-bottom:1px solid #e8eef6; }
.sal-table tr:last-child { border-bottom:none; font-weight:600; color:#0d2b5e; }
.sal-table td { padding:7px 4px; font-size:13px; color:#2d3748; }
.sal-table td:last-child { text-align:right; font-weight:500; color:#1a56b0; }
.sal-table tr.gross td { background:#f0f5ff; font-weight:600; }
.sal-table tr.ctc td { background:#e8f0fe; font-weight:700; color:#0d2b5e; }
div[data-testid="stTabs"] { background:#fff; border-radius:10px; border:1px solid #dbe3ed; padding:0; box-shadow:0 1px 4px rgba(0,0,0,0.04); }
div[data-testid="stTabs"] > div:first-child { background:#f5f8ff; border-bottom:2px solid #dbe3ed; border-radius:10px 10px 0 0; padding:0 16px; }
div[data-testid="stTabs"] button { font-size:13px; font-weight:500; color:#6b7c93; padding:12px 20px; border:none; background:transparent; }
div[data-testid="stTabs"] button[aria-selected="true"] { color:#1a56b0; border-bottom:2px solid #1a56b0; font-weight:600; }
div[data-testid="stTabs"] > div:last-child { padding:24px; }
.stButton > button { background:#1a56b0 !important; color:white !important; border:none !important; border-radius:7px !important; font-weight:600 !important; font-size:13px !important; padding:10px 20px !important; width:100% !important; }
.stButton > button:hover { background:#1344a0 !important; }
.stButton > button p, .stButton > button span, .stButton > button div { color:white !important; }
.stDownloadButton > button { background:#f0f5ff !important; color:#1a56b0 !important; border:1.5px solid #1a56b0 !important; border-radius:7px !important; font-weight:600 !important; font-size:13px !important; width:100% !important; }
.stDownloadButton > button p, .stDownloadButton > button span { color:#1a56b0 !important; }
.stSelectbox label, .stTextInput label, .stDateInput label, .stTextArea label { font-weight:600; font-size:12px; color:#4a5568; text-transform:uppercase; letter-spacing:0.4px; }
.field-group-label { font-size:12px; font-weight:700; color:#1a56b0; text-transform:uppercase; letter-spacing:0.5px; margin:16px 0 10px; padding-left:2px; }
.aa-info    { background:#f0f5ff; border-left:3px solid #1a56b0; border-radius:6px; padding:10px 14px; font-size:13px; color:#1a2942; margin:8px 0; }
.aa-success { background:#f0fdf4; border-left:3px solid #22c55e; border-radius:6px; padding:10px 14px; font-size:13px; color:#166534; margin:8px 0; }
.aa-error   { background:#fff5f5; border-left:3px solid #ef4444; border-radius:6px; padding:10px 14px; font-size:13px; color:#991b1b; margin:8px 0; }
.parsed-box { background:#f5f8ff; border:1px solid #c3d4f0; border-radius:7px; padding:10px 14px; font-size:12px; color:#2d3748; margin:8px 0 12px; line-height:1.8; }
.parsed-box span { font-weight:600; color:#1a56b0; }
.dur-badge { background:#e8f0fe; color:#1a56b0; border-radius:20px; padding:3px 12px; font-size:12px; font-weight:600; display:inline-block; margin:6px 0; }
.fix-badge { background:#fff7ed; border:1px solid #f97316; color:#c2410c; border-radius:6px; padding:4px 10px; font-size:11px; margin:4px 0; display:inline-block; }
.preview-rr { background:#f8faff; border:1px solid #dbe3ed; border-radius:8px; padding:12px 16px; margin-top:8px; font-size:13px; }
</style>
""", unsafe_allow_html=True)

# ─── Top Bar ──────────────────────────────────────────────────
logo_url = "https://raw.githubusercontent.com/Analytics-Avenue/streamlit-dataapp/main/logo.png"
st.markdown(f"""
<div class="aa-topbar">
    <img src="{logo_url}" width="48" style="border-radius:6px;border:1px solid #dbe3ed;">
    <div>
        <div class="aa-topbar-name">Analytics Avenue LLP</div>
        <div class="aa-topbar-sub">Empower your business with data-driven insights</div>
    </div>
    <div style="flex:1;"></div>
    <div style="font-size:12px;color:#7a8fa6;">HR Automation Platform</div>
</div>
""", unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs([
    "Pre-Offer Letter", "Offer Letter", "Internship Certificate", "History"
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
            salutation_pre = st.selectbox("Salutation", ["Ms.", "Mr."], key="pre_sal")
        with col_b:
            role_pre_sel = st.selectbox("Role / Designation", PRESET_ROLES, key="pre_role_sel")

        if role_pre_sel == "Other":
            role_pre_raw = st.text_input("Type Role Name", placeholder="e.g. Data Science Analyst", key="pre_role_other")
            role_pre = fix_role_name(role_pre_raw) if role_pre_raw.strip() else ""
            if role_pre_raw.strip() and role_pre != role_pre_raw.strip():
                st.markdown(f'<div class="fix-badge">✏️ Auto-corrected: <b>{role_pre}</b></div>', unsafe_allow_html=True)

            # R&R for Other role in pre-offer
            st.markdown('<div class="field-group-label">Roles &amp; Responsibilities</div>', unsafe_allow_html=True)
            st.caption("Enter each point on a new line — spelling & grammar auto-fixed, minimum 5 points auto-added")
            pre_rr_raw = st.text_area("Responsibilities", height=130,
                placeholder="e.g.\ndesign and develop scalable applications\nmanage client requirements",
                key="pre_rr_other")
            pre_rr_lines = [l.strip() for l in pre_rr_raw.split("\n") if l.strip()]
            pre_rr_fixed = complete_responsibilities(pre_rr_lines, role_pre or "General", min_points=5)
            if pre_rr_lines:
                st.markdown('<div class="preview-rr"><b>Preview (auto-corrected):</b><br>' +
                    '<br>'.join(f'• {l}' for l in pre_rr_fixed) + '</div>', unsafe_allow_html=True)
        else:
            role_pre = role_pre_sel
            pre_rr_fixed = []

        joining_date_pre = st.date_input("Joining Date", value=date.today(), key="pre_join")
        letter_date_pre  = st.date_input("Letter Date",  value=date.today(), key="pre_letter_date")

        # Training & Probation Period checkboxes
        st.markdown('<div class="field-group-label">Training &amp; Probation Period</div>', unsafe_allow_html=True)
        
        col_tr, col_pr = st.columns(2)
        with col_tr:
            has_training = st.checkbox("Include Training Period", key="pre_has_training")
        with col_pr:
            has_probation = st.checkbox("Include Probation Period", value=True, key="pre_has_probation")

        training_end = joining_date_pre
        training_dur = None
        probation_start = None

        if has_training:
            training_dur = st.selectbox("Training Duration",
                ["15 days", "1 month", "2 months", "3 months"], key="pre_training_dur")
            if "day" in training_dur:
                days_n = int(training_dur.split()[0])
                training_end = joining_date_pre + timedelta(days=days_n)
            else:
                months_n = int(training_dur.split()[0])
                training_end = joining_date_pre + relativedelta(months=months_n)
            st.markdown(f'<div class="dur-badge">Training: {joining_date_pre.strftime("%d %b %Y")} → {training_end.strftime("%d %b %Y")}</div>', unsafe_allow_html=True)

        if has_probation:
            probation_start = training_end
            st.markdown(f'<div class="dur-badge">Probation starts: {probation_start.strftime("%d %b %Y")}</div>', unsafe_allow_html=True)

        # CTC Range
        st.markdown('<div class="field-group-label">Post-Confirmation CTC Range</div>', unsafe_allow_html=True)
        ctc_range_sel = st.selectbox("CTC Range (Post Confirmation)", CTC_RANGES, key="pre_ctc_range")
        if ctc_range_sel == "Other (Custom Range)":
            col_min, col_max = st.columns(2)
            with col_min:
                ctc_min_raw = st.text_input("Min CTC (LPA)", placeholder="e.g. 3", key="pre_ctc_min")
            with col_max:
                ctc_max_raw = st.text_input("Max CTC (LPA)", placeholder="e.g. 6", key="pre_ctc_max")
            try:
                ctc_range_display = f"₹{float(ctc_min_raw):.0f} LPA to ₹{float(ctc_max_raw):.0f} LPA" if ctc_min_raw and ctc_max_raw else "₹4 LPA to ₹6 LPA"
            except Exception:
                ctc_range_display = "₹4 LPA to ₹6 LPA"
        else:
            # Convert "₹3 LPA – ₹5 LPA" to "₹3 LPA to ₹5 LPA"
            ctc_range_display = ctc_range_sel.replace("–", "to")

        # Compensation
        st.markdown('<div class="field-group-label">Probation Compensation</div>', unsafe_allow_html=True)
        col_s, col_i = st.columns(2)
        with col_s:
            stipend_sel = st.selectbox("Fixed Stipend / Base Pay",
                ["\u20b910,000", "\u20b912,000", "\u20b915,000", "Other"], key="pre_stipend_sel")
            if stipend_sel == "Other":
                stipend_raw = st.text_input("Enter Stipend Amount", placeholder="e.g. 13000", key="pre_stipend_other")
                stipend_pre = format_amount(stipend_raw) if stipend_raw.strip() else ""
                if stipend_pre:
                    st.markdown(f'<div class="fix-badge">Formatted: <b>{stipend_pre}</b></div>', unsafe_allow_html=True)
            else:
                stipend_pre = stipend_sel

        with col_i:
            incentive_sel = st.selectbox("Performance Incentive (Up to)",
                ["None", "\u20b915,000", "\u20b918,000", "\u20b920,000", "Other"], key="pre_incentive_sel")
            if incentive_sel == "Other":
                incentive_raw = st.text_input("Enter Incentive Amount", placeholder="e.g. 22000", key="pre_incentive_other")
                incentive_pre = format_amount(incentive_raw) if incentive_raw.strip() else ""
                if incentive_pre:
                    st.markdown(f'<div class="fix-badge">Formatted: <b>{incentive_pre}</b></div>', unsafe_allow_html=True)
            elif incentive_sel == "None":
                incentive_pre = ""
            else:
                incentive_pre = incentive_sel

    with col2:
        st.markdown('<div class="field-group-label">Preview &amp; Generate</div>', unsafe_allow_html=True)
        training_line   = f"<b>Training:</b> {training_dur}<br>" if has_training else ""
        probation_line  = f"<b>Probation Starts:</b> {probation_start.strftime('%d %b %Y')}<br>" if has_probation and probation_start else ""
        incentive_line  = f"<b>Incentive:</b> Up to {incentive_pre} / month<br>" if incentive_pre else "<b>Incentive:</b> Not applicable<br>"
        st.markdown(f"""
        <div class="aa-card">
            <div style="font-size:13px;color:#4a5568;line-height:2;">
                <b>Candidate:</b> {pre_name_typed.strip() or "—"}<br>
                <b>Role:</b> {role_pre or "—"}<br>
                <b>Joining:</b> {joining_date_pre.strftime("%d %b %Y")}<br>
                {training_line}
                {probation_line}
                <b>Stipend:</b> {stipend_pre or "—"} / month<br>
                {incentive_line}
                <b>CTC Range:</b> {ctc_range_display}
            </div>
        </div>
        """, unsafe_allow_html=True)

        generate_pre = st.button("Generate Pre-Offer Letter", key="gen_pre", use_container_width=True)

        if generate_pre:
            candidate_name = pre_name_typed.strip()
            if not candidate_name:
                st.error("Please enter candidate name.")
            elif not role_pre:
                st.error("Please enter a role.")
            elif not stipend_pre:
                st.error("Please select or enter stipend amount.")
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
                        ctc_range=ctc_range_display,
                        training_period=training_dur,
                        probation_start=probation_start.strftime("%d-%m-%Y") if has_probation and probation_start else None,
                        has_probation=has_probation,
                        custom_rr=pre_rr_fixed if pre_rr_fixed else None,
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
            st.markdown(f'<div class="aa-success">✅ Letter ready: {r["filename"]}</div>', unsafe_allow_html=True)
            col_dl1, col_dl2 = st.columns(2)
            with col_dl1:
                st.download_button("⬇️ Download DOCX", data=read_file_bytes(r["docx_path"]),
                    file_name=f"{r['filename']}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    key="persist_pre_docx")
            with col_dl2:
                if r.get("pdf_path") and os.path.exists(r["pdf_path"]):
                    st.download_button("⬇️ Download PDF", data=read_file_bytes(r["pdf_path"]),
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
            salutation_offer = st.selectbox("Salutation", ["Ms.", "Mr."], key="offer_sal")
        with col_b:
            role_offer_sel = st.selectbox("Designation", PRESET_ROLES, key="offer_role_sel")

        if role_offer_sel == "Other":
            role_offer_raw = st.text_input("Type Role Name", placeholder="e.g. Cloud Solutions Engineer", key="offer_role_other")
            role_offer = fix_role_name(role_offer_raw) if role_offer_raw.strip() else ""
            if role_offer_raw.strip() and role_offer != role_offer_raw.strip():
                st.markdown(f'<div class="fix-badge">✏️ Auto-corrected: <b>{role_offer}</b></div>', unsafe_allow_html=True)

            st.markdown('<div class="field-group-label">Roles &amp; Responsibilities</div>', unsafe_allow_html=True)
            st.caption("Enter each point on a new line — auto-fixed & minimum 5 points added")
            rr_raw = st.text_area("Responsibilities", height=140,
                placeholder="e.g.\ndesign and devlop web applications\nmanage databse and apis",
                key="offer_rr_other")
            rr_lines = [l.strip() for l in rr_raw.split("\n") if l.strip()]
            rr_fixed = complete_responsibilities(rr_lines, role_offer or "General", min_points=5)
            if rr_lines:
                st.markdown('<div class="preview-rr"><b>Preview (auto-corrected):</b><br>' +
                    '<br>'.join(f'• {l}' for l in rr_fixed) + '</div>', unsafe_allow_html=True)
        else:
            role_offer = role_offer_sel
            rr_fixed = []

        dept_offer         = st.selectbox("Department", ["Analytics", "Technology", "HR", "Business Development", "Marketing", "Finance", "Operations"], key="offer_dept")
        joining_date_offer = st.date_input("Joining Date", value=date.today(), key="offer_join")
        letter_date_offer  = st.date_input("Letter Date",  value=date.today(), key="offer_letter_date")

    with col2:
        st.markdown('<div class="field-group-label">Salary Structure</div>', unsafe_allow_html=True)
        salary_prompt = st.text_area("Salary Prompt",
            placeholder='e.g. "6 LPA, 40% basic, no PF, 10% variable"\n"5 LPA, basic 4 LPA, PF 12% on 70% CTC"',
            height=80, key="salary_prompt")

        parse_salary_btn = st.button("Calculate Salary Breakup", key="parse_salary")

        if "salary_params" not in st.session_state: st.session_state.salary_params = None
        if "salary_result" not in st.session_state: st.session_state.salary_result = None

        if parse_salary_btn and salary_prompt:
            with st.spinner("Parsing salary structure..."):
                params = parse_salary_prompt_groq(salary_prompt, model="llama3-8b-8192")
                st.session_state.salary_params = params
                st.session_state.salary_result = params

        if st.session_state.salary_params:
            p = st.session_state.salary_params
            pf_display = "Not applicable" if p.get("pf_percent", 0) == 0 else f"{p.get('pf_percent', 0)}% of Basic"
            st.markdown(f"""
            <div class="parsed-box">
                <span>CTC:</span> &#8377;{p['ctc_annual']:,.0f} &nbsp;|&nbsp;
                <span>Basic:</span> {p.get('base_percent',0)}% of CTC &nbsp;|&nbsp;
                <span>HRA:</span> {p.get('hra_percent',0)}% of Basic<br>
                <span>PF:</span> {pf_display} &nbsp;|&nbsp;
                <span>Variable:</span> {p.get('variable_percent',0)}% of CTC
            </div>
            """, unsafe_allow_html=True)

        if st.session_state.salary_result:
            s = st.session_state.salary_result
            st.markdown(f"""
            <table class="sal-table">
                <tr><td>Basic Salary</td><td>{s.get('basic_monthly_str','—')}/mo</td></tr>
                <tr><td>HRA</td><td>{s.get('hra_monthly_str','—')}/mo</td></tr>
                <tr><td>PF — Employer</td><td>{s.get('pf_monthly_str','—')}/mo</td></tr>
                <tr><td>Special Allowance</td><td>{s.get('special_allowance_monthly_str','—')}/mo</td></tr>
                <tr class="gross"><td><b>Gross Monthly</b></td><td><b>{s.get('gross_monthly_str','—')}</b></td></tr>
                <tr><td>Variable Pay (Annual)</td><td>{s.get('variable_annual_str','—')}</td></tr>
                <tr class="ctc"><td><b>Total CTC (Annual)</b></td><td><b>{s.get('ctc_annual_str','—')}</b></td></tr>
            </table>
            """, unsafe_allow_html=True)

        st.markdown("")
        generate_offer = st.button("Generate Offer Letter", key="gen_offer", use_container_width=True)

        if generate_offer:
            if not offer_name_typed.strip():
                st.error("Please enter a candidate name.")
            elif not role_offer:
                st.error("Please enter a role designation.")
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
                        base_percent=p.get("base_percent", 40),
                        hra_percent=p.get("hra_percent", 20),
                        pf_percent=p.get("pf_percent", 5.0),
                        variable_percent=p.get("variable_percent", 10),
                        letter_date=letter_date_offer.strftime("%d-%m-%Y"),
                        custom_rr=rr_fixed if rr_fixed else None,
                        salary_data=st.session_state.salary_result,
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
            st.markdown(f'<div class="aa-success">✅ Letter ready: {r["filename"]}</div>', unsafe_allow_html=True)
            col_dl1, col_dl2 = st.columns(2)
            with col_dl1:
                st.download_button("⬇️ Download DOCX", data=read_file_bytes(r["docx_path"]),
                    file_name=f"{r['filename']}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    key="persist_offer_docx")
            with col_dl2:
                if r.get("pdf_path") and os.path.exists(r["pdf_path"]):
                    st.download_button("⬇️ Download PDF", data=read_file_bytes(r["pdf_path"]),
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
            salutation_intern = st.selectbox("Salutation", ["Ms.", "Mr."], key="intern_sal")
        with col_b:
            reg_no = st.text_input("Reg. No.", key="intern_reg")
        college = st.text_input("College / Institution", key="intern_college")
        col_c, col_d = st.columns(2)
        with col_c:
            dept_intern = st.selectbox("Department", COLLEGE_DEPARTMENTS, key="intern_dept")
            if dept_intern == "Other":
                dept_intern_raw = st.text_input("Type Department", placeholder="e.g. Robotics Engineering", key="intern_dept_other")
                dept_intern = fix_role_name(dept_intern_raw) if dept_intern_raw.strip() else ""
        with col_d:
            role_intern_sel = st.selectbox("Role", PRESET_ROLES, key="intern_role_sel")

        if role_intern_sel == "Other":
            role_intern_raw = st.text_input("Type Role Name", placeholder="e.g. Full Stack Developer Intern", key="intern_role_other")
            role_intern = fix_role_name(role_intern_raw) if role_intern_raw.strip() else ""
            if role_intern_raw.strip() and role_intern != role_intern_raw.strip():
                st.markdown(f'<div class="fix-badge">✏️ Auto-corrected: <b>{role_intern}</b></div>', unsafe_allow_html=True)
        else:
            role_intern = role_intern_sel

    with col2:
        st.markdown('<div class="field-group-label">Internship Period</div>', unsafe_allow_html=True)
        date_mode = st.radio("Date Entry Mode",
            ["Manual (pick start & end)", "Auto (start + duration)"],
            horizontal=True, key="intern_date_mode")

        if date_mode == "Manual (pick start & end)":
            col_a, col_b = st.columns(2)
            with col_a:
                start_date_intern = st.date_input("Start Date", value=date.today(), key="intern_start_manual")
            with col_b:
                end_date_intern = st.date_input("End Date", value=date.today(), key="intern_end_manual")
            delta = relativedelta(end_date_intern, start_date_intern)
            months = delta.months + delta.years * 12
            days   = delta.days
            DWORDS = {1:"one",2:"two",3:"three",4:"four",5:"five",6:"six",
                      7:"seven",8:"eight",9:"nine",10:"ten",11:"eleven",12:"twelve"}
            if months > 0 and days == 0:
                duration_intern = f"{DWORDS.get(months, str(months))} month{'s' if months>1 else ''}"
            elif months > 0:
                duration_intern = f"{months} month{'s' if months>1 else ''} and {days} day{'s' if days>1 else ''}"
            elif days > 0:
                duration_intern = f"{days} day{'s' if days>1 else ''}"
            else:
                duration_intern = "—"
            st.markdown(f'<div class="dur-badge">Duration: {duration_intern}</div>', unsafe_allow_html=True)
        else:
            start_date_intern = st.date_input("Start Date", value=date.today(), key="intern_start_auto")
            duration_months_n = st.selectbox("Duration", [1,2,3,4,6], key="intern_dur_months",
                format_func=lambda x: f"{x} month{'s' if x>1 else ''}")
            end_date_intern = start_date_intern + relativedelta(months=duration_months_n)
            DWORDS = {1:"one",2:"two",3:"three",4:"four",5:"five",6:"six"}
            duration_intern = f"{DWORDS.get(duration_months_n, str(duration_months_n))} month{'s' if duration_months_n>1 else ''}"
            st.markdown(f'<div class="dur-badge">End: {end_date_intern.strftime("%d %b %Y")} &nbsp;|&nbsp; Duration: {duration_intern}</div>', unsafe_allow_html=True)

        letter_date_intern = st.date_input("Letter Date", value=date.today(), key="intern_letter_date")

        st.markdown('<div class="field-group-label">Responsibilities</div>', unsafe_allow_html=True)
        st.caption("Auto-filled from role — editable. Spelling & grammar auto-fixed, minimum 5 points ensured.")

        if role_intern_sel == "Other":
            default_resp = ""
        else:
            auto_resp    = get_responsibilities_for_role(role_intern)
            default_resp = "\n".join(auto_resp)

        responsibilities_text = st.text_area("Responsibilities", value=default_resp,
            height=140, key=f"intern_resp_{role_intern}", label_visibility="collapsed")

        st.markdown("")
        generate_intern = st.button("Generate Internship Certificate", key="gen_intern", use_container_width=True)

        if generate_intern:
            intern_name = intern_name_typed.strip()
            if not intern_name:
                st.error("Please enter an intern name.")
            elif not role_intern:
                st.error("Please enter a role.")
            else:
                raw_lines = [l.strip() for l in responsibilities_text.split("\n") if l.strip()]
                responsibilities = complete_responsibilities(raw_lines, role_intern, min_points=5)
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
            st.markdown(f'<div class="aa-success">✅ Certificate ready: {r["filename"]}</div>', unsafe_allow_html=True)
            col_dl1, col_dl2 = st.columns(2)
            with col_dl1:
                st.download_button("⬇️ Download DOCX", data=read_file_bytes(r["docx_path"]),
                    file_name=f"{r['filename']}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    key="persist_intern_docx")
            with col_dl2:
                if r.get("pdf_path") and os.path.exists(r["pdf_path"]):
                    st.download_button("⬇️ Download PDF", data=read_file_bytes(r["pdf_path"]),
                        file_name=f"{r['filename']}.pdf", mime="application/pdf",
                        key="persist_intern_pdf")


# ══════════════════════════════════════════════
# TAB 4 — HISTORY
# ══════════════════════════════════════════════
with tab4:
    st.markdown('<div class="aa-page-title">Document History</div>', unsafe_allow_html=True)
    history = load_history()
    if not history:
        st.markdown('<div class="aa-info">No documents generated yet.</div>', unsafe_allow_html=True)
    else:
        for i, record in enumerate(history):
            with st.expander(f"{record.get('type','—')} · {record.get('candidate_name','—')} · {record.get('generated_at','')}"):
                c1, c2, c3 = st.columns(3)
                c1.caption(f"**Type:** {record.get('type','—')}")
                c2.caption(f"**Name:** {record.get('candidate_name','—')}")
                c3.caption(f"**Role:** {record.get('role','—')}")
                dl1, dl2 = st.columns(2)
                if record.get("docx_path") and os.path.exists(record["docx_path"]):
                    with dl1:
                        st.download_button("⬇️ DOCX", data=read_file_bytes(record["docx_path"]),
                            file_name=f"{record['filename']}.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            key=f"hist_docx_{i}")
                if record.get("pdf_path") and os.path.exists(record["pdf_path"]):
                    with dl2:
                        st.download_button("⬇️ PDF", data=read_file_bytes(record["pdf_path"]),
                            file_name=f"{record['filename']}.pdf",
                            mime="application/pdf", key=f"hist_pdf_{i}")
