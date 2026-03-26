"""
app.py
Analytics Avenue LLP — HR Letter Generator
Streamlit UI
"""

import os
import sys
import streamlit as st
from datetime import datetime, date

# Add project root to path
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
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ───────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    .main-header {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        color: white;
        padding: 24px 32px;
        border-radius: 12px;
        margin-bottom: 24px;
        display: flex;
        align-items: center;
        gap: 20px;
    }
    .main-header-text h1 {
        font-size: 22px;
        font-weight: 600;
        margin: 0;
        color: white;
    }
    .main-header-text p {
        font-size: 13px;
        color: rgba(255,255,255,0.6);
        margin: 4px 0 0;
    }
    .company-logo-bar {
        background: white;
        border: 1px solid #e8e8e8;
        border-radius: 12px;
        padding: 16px 24px;
        margin-bottom: 20px;
        display: flex;
        align-items: center;
        gap: 14px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    }
    .section-card {
        background: white;
        border: 1px solid #e8e8e8;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 16px;
    }
    .salary-preview {
        background: #f8f9ff;
        border: 1px solid #e0e4ff;
        border-radius: 8px;
        padding: 16px;
        font-size: 13px;
    }
    .salary-row {
        display: flex;
        justify-content: space-between;
        padding: 4px 0;
        border-bottom: 1px solid #eee;
    }
    .success-box {
        background: #f0fff4;
        border: 1px solid #68d391;
        border-radius: 8px;
        padding: 16px;
        color: #276749;
    }
    .error-box {
        background: #fff5f5;
        border: 1px solid #fc8181;
        border-radius: 8px;
        padding: 16px;
        color: #c53030;
    }
    div[data-testid="stTabs"] button {
        font-size: 14px;
        font-weight: 500;
    }
    .stButton > button {
        background: #1a1a2e;
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: 500;
        padding: 10px 24px;
        width: 100%;
    }
    .stButton > button:hover {
        background: #16213e;
        color: white;
    }
    .stSelectbox label, .stTextInput label, .stDateInput label {
        font-weight: 500;
        font-size: 13px;
        color: #374151;
    }
    .badge {
        display: inline-block;
        background: #e8f4fd;
        color: #1565c0;
        padding: 2px 10px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 500;
    }
</style>
""", unsafe_allow_html=True)


# ─── Company Logo Bar ─────────────────────────────────────────
logo_url = "https://raw.githubusercontent.com/Analytics-Avenue/streamlit-dataapp/main/logo.png"

st.markdown(f"""
<div class="company-logo-bar">
    <img src="{logo_url}" width="56" style="margin-right:4px; border-radius:6px;">
    <div style="line-height:1.2;">
        <div style="color:#064b86; font-size:22px; font-weight:700; margin:0;">Analytics Avenue LLP</div>
        <div style="color:#666; font-size:13px; margin-top:2px;">(Empower your business with data-driven insights)</div>
    </div>
</div>
""", unsafe_allow_html=True)


# ─── Header ───────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <div class="main-header-text">
        <h1>📄 HR Letter Generator</h1>
        <p>Generate Pre-Offer Letters, Offer Letters & Internship Completion Certificates instantly</p>
    </div>
</div>
""", unsafe_allow_html=True)


# ─── Sidebar ──────────────────────────────────────────────────
with st.sidebar:

    st.markdown(f"""
    <div style="display:flex; align-items:center; gap:10px; margin-bottom:16px;">
        <img src="{logo_url}" width="36" style="border-radius:4px;">
        <div style="line-height:1.2;">
            <div style="color:#064b86; font-size:14px; font-weight:700;">Analytics Avenue LLP</div>
            <div style="color:#888; font-size:11px;">HR Automation</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    st.markdown("### ➕ Add New Person")
    person_type = st.radio("Type", ["Candidate", "Intern"], horizontal=True)

    with st.expander("Add to Database", expanded=False):
        if person_type == "Candidate":
            new_name = st.text_input("Full Name*")
            new_sal = st.selectbox("Salutation*", ["Ms.", "Mr.", "Dr."])
            new_role = st.selectbox("Role*", get_roles())
            new_dept = st.selectbox("Department*", get_departments())
            new_join = st.date_input("Joining Date*")
            new_email = st.text_input("Email")
            if st.button("Add Candidate"):
                if new_name:
                    add_candidate({
                        "name": new_name,
                        "salutation": new_sal,
                        "role": new_role,
                        "department": new_dept,
                        "joining_date": new_join.strftime("%d-%m-%Y"),
                        "email": new_email,
                        "phone": ""
                    })
                    st.success(f"✅ {new_name} added!")
                    st.rerun()
        else:
            new_name = st.text_input("Full Name*")
            new_sal = st.selectbox("Salutation*", ["Ms.", "Mr.", "Dr."])
            new_reg = st.text_input("Reg. No.")
            new_college = st.text_input("College / Institution")
            new_dept = st.selectbox("Department*", get_departments())
            new_role = st.selectbox("Role*", get_roles())
            new_start = st.date_input("Start Date*")
            new_end = st.date_input("End Date*")
            new_email = st.text_input("Email")
            if st.button("Add Intern"):
                if new_name:
                    add_intern({
                        "name": new_name,
                        "salutation": new_sal,
                        "reg_no": new_reg,
                        "college": new_college,
                        "department": new_dept,
                        "role": new_role,
                        "start_date": new_start.strftime("%d-%m-%Y"),
                        "end_date": new_end.strftime("%d-%m-%Y"),
                        "duration": "",
                        "responsibilities": [],
                        "email": new_email
                    })
                    st.success(f"✅ {new_name} added!")
                    st.rerun()

    st.divider()
    st.markdown("### ⚙️ Settings")
    st.caption("Groq Model")
    groq_model = st.selectbox("Model", [
        "llama3-8b-8192",
        "llama3-70b-8192",
        "mixtral-8x7b-32768",
        "gemma2-9b-it"
    ], label_visibility="collapsed")

    st.divider()
    st.caption("Analytics Avenue LLP · HR Automation")


# ─── Main Tabs ────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "📋 Pre-Offer Letter",
    "💼 Offer Letter",
    "🎓 Internship Letter",
    "🕐 History"
])


# ══════════════════════════════════════════════
# TAB 1: PRE-OFFER LETTER
# ══════════════════════════════════════════════
with tab1:
    st.markdown("#### Pre-Offer Letter Generation")
    st.caption("Generates a pre-offer letter based on candidate details. All policy points are auto-included from the template.")

    col1, col2 = st.columns([1, 1], gap="large")

    with col1:
        st.markdown("**Candidate Details**")

    with col2:
        pre_name_typed = st.text_input("Candidate Name *", placeholder="Type candidate full name", key="pre_name_manual")
        candidate_name_pre_final = pre_name_typed.strip()
        pre_data = {}

        col_a, col_b = st.columns(2)
        with col_a:
            salutation_pre = st.selectbox("Salutation *", ["Ms.", "Mr.", "Dr."],
                                           index=["Ms.", "Mr.", "Dr."].index(pre_data.get("salutation", "Ms.")),
                                           key="pre_sal")
        with col_b:
            role_pre = st.selectbox("Role / Designation *",
                                     get_roles(),
                                     index=get_roles().index(pre_data.get("role", get_roles()[0])) if pre_data.get("role") in get_roles() else 0,
                                     key="pre_role")

        default_join = date.today()
        if pre_data.get("joining_date"):
            try:
                default_join = datetime.strptime(pre_data["joining_date"], "%d-%m-%Y").date()
            except:
                pass

        joining_date_pre = st.date_input("Joining Date *", value=default_join, key="pre_join")
        letter_date_pre = st.date_input("Letter Date *", value=date.today(), key="pre_letter_date")

        st.markdown("**Compensation During Probation**")
        col_s, col_i = st.columns(2)
        with col_s:
            stipend_pre = st.selectbox(
                "Fixed Stipend / Base Pay *",
                ["₹10,000", "₹12,000", "₹15,000"],
                key="pre_stipend"
            )
        with col_i:
            incentive_pre = st.selectbox(
                "Performance-Based Incentive (Up to) *",
                ["₹15,000", "₹18,000", "₹20,000"],
                key="pre_incentive"
            )

        st.markdown("")
        generate_pre = st.button("📄 Generate Pre-Offer Letter", key="gen_pre", use_container_width=True)

        if generate_pre:
            candidate_name = candidate_name_pre_final.strip()
            if not candidate_name:
                st.error("Please select or type a candidate name.")
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
                    if pre_name_typed.strip() and pre_name_typed.strip() not in get_candidate_names():
                        add_candidate({"name": pre_name_typed.strip(), "salutation": salutation_pre, "role": role_pre, "department": "Analytics", "joining_date": joining_date_pre.strftime("%d-%m-%Y"), "email": "", "phone": ""})
                        st.success(f"✅ {pre_name_typed.strip()} saved to database!")
                    st.success(f"✅ Letter generated: {result['filename']}")
                    st.session_state["pre_result"] = result
                else:
                    st.error(f"❌ Error: {result['error']}")
                    if "Template not found" in str(result['error']):
                        st.warning("📁 Please add `pre_offer_template.docx` to the `templates/` folder.")

        if st.session_state.get("pre_result"):
            r = st.session_state["pre_result"]
            st.success(f"✅ Ready: {r['filename']}")
            col_dl1, col_dl2 = st.columns(2)
            with col_dl1:
                st.download_button(
                    "⬇️ Download DOCX",
                    data=read_file_bytes(r["docx_path"]),
                    file_name=f"{r['filename']}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    key="persist_pre_docx"
                )
            with col_dl2:
                if r.get("pdf_path") and os.path.exists(r["pdf_path"]):
                    st.download_button(
                        "⬇️ Download PDF",
                        data=read_file_bytes(r["pdf_path"]),
                        file_name=f"{r['filename']}.pdf",
                        mime="application/pdf",
                        key="persist_pre_pdf"
                    )


# ══════════════════════════════════════════════
# TAB 2: OFFER LETTER
# ══════════════════════════════════════════════
with tab2:
    st.markdown("#### Offer Letter Generation")
    st.caption("Generates a full offer letter with auto-calculated salary breakup table.")

    col1, col2 = st.columns([1, 1], gap="large")

    with col1:
        st.markdown("**Candidate Details**")

        offer_name_typed = st.text_input("Candidate Name *", placeholder="Type candidate full name", key="offer_name_manual")
        candidate_name_offer_final = offer_name_typed.strip()
        offer_data = {}

        col_a, col_b = st.columns(2)
        with col_a:
            salutation_offer = st.selectbox("Salutation *", ["Ms.", "Mr.", "Dr."],
                                             index=["Ms.", "Mr.", "Dr."].index(offer_data.get("salutation", "Ms.")),
                                             key="offer_sal")
        with col_b:
            role_offer = st.selectbox("Designation *", get_roles(),
                                       index=get_roles().index(offer_data.get("role", get_roles()[0])) if offer_data.get("role") in get_roles() else 0,
                                       key="offer_role")

        dept_offer = st.selectbox("Department *", get_departments(),
                                   index=get_departments().index(offer_data.get("department", get_departments()[0])) if offer_data.get("department") in get_departments() else 0,
                                   key="offer_dept")

        default_join_offer = date.today()
        if offer_data.get("joining_date"):
            try:
                default_join_offer = datetime.strptime(offer_data["joining_date"], "%d-%m-%Y").date()
            except:
                pass

        joining_date_offer = st.date_input("Joining Date *", value=default_join_offer, key="offer_join")
        letter_date_offer = st.date_input("Letter Date *", value=date.today(), key="offer_letter_date")

    with col2:
        st.markdown("**Salary Details — Prompt Box**")
        st.caption("Type CTC and salary structure in plain English")

        salary_prompt = st.text_area(
            "Salary Prompt *",
            placeholder='e.g. "6 LPA, 40% base, PF yes, 10% variable"\nor "5.5 LPA, base 45%, no PF, variable 15%"',
            height=90,
            key="salary_prompt"
        )

        parse_salary_btn = st.button("🔢 Calculate Salary Breakup", key="parse_salary")

        if "salary_params" not in st.session_state:
            st.session_state.salary_params = None
        if "salary_result" not in st.session_state:
            st.session_state.salary_result = None

        if parse_salary_btn and salary_prompt:
            with st.spinner("Calculating..."):
                params = parse_salary_prompt_groq(salary_prompt, model=groq_model)
                st.session_state.salary_params = params

                # ── FIX: Use params directly — NO hardcoded fallback defaults here ──
                # All defaults are already handled correctly inside parse_salary_prompt_groq
                st.session_state.salary_result = calculate_salary_breakup(
                    ctc_annual=params["ctc_annual"],
                    base_percent=params["base_percent"],
                    hra_percent=params["hra_percent"],
                    pf_percent=params["pf_percent"],
                    variable_percent=params["variable_percent"],
                )

            # Show debug info so HR can verify parsing
            with st.expander("🔍 Parsed Parameters (click to verify)", expanded=False):
                p = st.session_state.salary_params
                st.caption(f"CTC: ₹{p['ctc_annual']:,.0f} | Basic: {p['base_percent']}% of CTC | "
                           f"HRA: {p['hra_percent']}% of Basic | "
                           f"PF: {'None' if p['pf_percent'] == 0 else str(p['pf_percent']) + '% of Basic'} | "
                           f"Variable: {p['variable_percent']}% of CTC")

        if st.session_state.salary_result:
            s = st.session_state.salary_result
            st.markdown("**Salary Breakup Preview**")
            preview_data = {
                "Basic (Monthly)":            s["basic_monthly_str"],
                "HRA (Monthly)":              s["hra_monthly_str"],
                "PF Employer (Monthly)":      s["pf_monthly_str"],
                "Special Allowance (Monthly)": s["special_allowance_monthly_str"],
                "Gross Monthly":              s["gross_monthly_str"],
                "Variable Pay (Annual)":      s["variable_annual_str"],
                "Total CTC":                  s["ctc_annual_str"],
            }
            for label, val in preview_data.items():
                cols = st.columns([3, 2])
                cols[0].caption(label)
                cols[1].caption(f"**{val}**")

        st.markdown("")
        generate_offer = st.button("📄 Generate Offer Letter", key="gen_offer", use_container_width=True)

        if generate_offer:
            candidate_name_offer = candidate_name_offer_final.strip()
            if not candidate_name_offer:
                st.error("Please select or type a candidate name.")
            elif not st.session_state.salary_result:
                st.error("Please calculate salary breakup first.")
            else:
                p = st.session_state.salary_params
                with st.spinner("Generating offer letter..."):
                    result = generate_offer_letter(
                        candidate_name=candidate_name_offer,
                        salutation=salutation_offer,
                        role=role_offer,
                        department=dept_offer,
                        joining_date=joining_date_offer.strftime("%d-%m-%Y"),
                        ctc_annual=p["ctc_annual"],
                        # ── FIX: Use params directly — NO hardcoded fallback defaults ──
                        base_percent=p["base_percent"],
                        hra_percent=p["hra_percent"],
                        pf_percent=p["pf_percent"],
                        variable_percent=p["variable_percent"],
                        letter_date=letter_date_offer.strftime("%d-%m-%Y"),
                    )

                if result["success"]:
                    if offer_name_typed.strip() and offer_name_typed.strip() not in get_candidate_names():
                        add_candidate({"name": offer_name_typed.strip(), "salutation": salutation_offer, "role": role_offer, "department": dept_offer, "joining_date": joining_date_offer.strftime("%d-%m-%Y"), "email": "", "phone": ""})
                        st.success(f"✅ {offer_name_typed.strip()} saved to database!")
                    st.success(f"✅ Letter generated: {result['filename']}")
                    st.session_state["offer_result"] = result
                else:
                    st.error(f"❌ Error: {result['error']}")
                    if "Template not found" in str(result['error']):
                        st.warning("📁 Please add `offer_letter_template.docx` to the `templates/` folder.")

        if st.session_state.get("offer_result"):
            r = st.session_state["offer_result"]
            st.success(f"✅ Ready: {r['filename']}")
            col_dl1, col_dl2 = st.columns(2)
            with col_dl1:
                st.download_button(
                    "⬇️ Download DOCX",
                    data=read_file_bytes(r["docx_path"]),
                    file_name=f"{r['filename']}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    key="persist_offer_docx"
                )
            with col_dl2:
                if r.get("pdf_path") and os.path.exists(r["pdf_path"]):
                    st.download_button(
                        "⬇️ Download PDF",
                        data=read_file_bytes(r["pdf_path"]),
                        file_name=f"{r['filename']}.pdf",
                        mime="application/pdf",
                        key="persist_offer_pdf"
                    )


# ══════════════════════════════════════════════
# TAB 3: INTERNSHIP LETTER
# ══════════════════════════════════════════════
with tab3:
    st.markdown("#### Internship Completion Letter")
    st.caption("Generates an internship completion certificate.")

    col1, col2 = st.columns([1, 1], gap="large")

    with col1:
        intern_name_typed = st.text_input("Intern Name *", placeholder="Type intern full name", key="intern_name_manual")
        intern_name_final = intern_name_typed.strip()
        intern_data = {}

        col_a, col_b = st.columns(2)
        with col_a:
            salutation_intern = st.selectbox("Salutation *", ["Ms.", "Mr.", "Dr."],
                                              index=["Ms.", "Mr.", "Dr."].index(intern_data.get("salutation", "Ms.")),
                                              key="intern_sal")
        with col_b:
            reg_no = st.text_input("Reg. No.", value=intern_data.get("reg_no", ""), key="intern_reg")

        college = st.text_input("College / Institution", value=intern_data.get("college", ""), key="intern_college")
        dept_intern = st.selectbox("Department *", get_departments(),
                                    index=get_departments().index(intern_data.get("department", get_departments()[0])) if intern_data.get("department") in get_departments() else 0,
                                    key="intern_dept")

        role_intern = st.selectbox("Role / Team *", get_roles(),
                                    index=get_roles().index(intern_data.get("role", get_roles()[0])) if intern_data.get("role") in get_roles() else 0,
                                    key="intern_role")

    with col2:
        default_start = date.today()
        default_end = date.today()
        if intern_data.get("start_date"):
            try:
                default_start = datetime.strptime(intern_data["start_date"], "%d-%m-%Y").date()
            except:
                pass
        if intern_data.get("end_date"):
            try:
                default_end = datetime.strptime(intern_data["end_date"], "%d-%m-%Y").date()
            except:
                pass

        col_a, col_b = st.columns(2)
        with col_a:
            start_date_intern = st.date_input("Start Date *", value=default_start, key="intern_start")
        with col_b:
            end_date_intern = st.date_input("End Date *", value=default_end, key="intern_end")

        duration_intern = st.text_input(
            "Duration (text)",
            value=intern_data.get("duration", ""),
            placeholder='e.g. "one month", "three months"',
            key="intern_duration"
        )

        letter_date_intern = st.date_input("Letter Date *", value=date.today(), key="intern_letter_date")

        if intern_data.get("responsibilities"):
            default_resp = "\n".join(intern_data.get("responsibilities", []))
        else:
            auto_resp = get_responsibilities_for_role(role_intern)
            default_resp = "\n".join(auto_resp)

        st.markdown("**Responsibilities** (auto-filled from role, editable)")
        responsibilities_text = st.text_area(
            "Responsibilities",
            value=default_resp,
            height=150,
            placeholder="Candidate sourcing and screening\nInterview scheduling\nHR support activities",
            key="intern_resp",
            label_visibility="collapsed"
        )

        st.markdown("")
        generate_intern = st.button("📄 Generate Internship Letter", key="gen_intern", use_container_width=True)

        if generate_intern:
            intern_name = intern_name_final.strip()
            if not intern_name:
                st.error("Please select or type an intern name.")
            else:
                responsibilities = [r.strip() for r in responsibilities_text.split("\n") if r.strip()]
                with st.spinner("Generating letter..."):
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
                    if intern_name_typed.strip() and intern_name_typed.strip() not in get_intern_names():
                        add_intern({
                            "name": intern_name_typed.strip(),
                            "salutation": salutation_intern,
                            "reg_no": reg_no,
                            "college": college,
                            "department": dept_intern,
                            "role": role_intern,
                            "start_date": start_date_intern.strftime("%d-%m-%Y"),
                            "end_date": end_date_intern.strftime("%d-%m-%Y"),
                            "duration": duration_intern,
                            "responsibilities": [r.strip() for r in responsibilities_text.split("\n") if r.strip()],
                            "email": ""
                        })
                        st.success(f"✅ {intern_name_typed.strip()} saved to database!")
                    st.success(f"✅ Letter generated: {result['filename']}")
                    st.session_state["intern_result"] = result
                else:
                    st.error(f"❌ Error: {result['error']}")
                    if "Template not found" in str(result['error']):
                        st.warning("📁 Please add `internship_template.docx` to the `templates/` folder.")

        if st.session_state.get("intern_result"):
            r = st.session_state["intern_result"]
            st.success(f"✅ Ready: {r['filename']}")
            col_dl1, col_dl2 = st.columns(2)
            with col_dl1:
                st.download_button(
                    "⬇️ Download DOCX",
                    data=read_file_bytes(r["docx_path"]),
                    file_name=f"{r['filename']}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    key="persist_intern_docx"
                )
            with col_dl2:
                if r.get("pdf_path") and os.path.exists(r["pdf_path"]):
                    st.download_button(
                        "⬇️ Download PDF",
                        data=read_file_bytes(r["pdf_path"]),
                        file_name=f"{r['filename']}.pdf",
                        mime="application/pdf",
                        key="persist_intern_pdf"
                    )


# ══════════════════════════════════════════════
# TAB 4: HISTORY
# ══════════════════════════════════════════════
with tab4:
    st.markdown("#### Document Generation History")
    st.caption("Last 100 generated documents")

    history = load_history()

    if not history:
        st.info("No documents generated yet. Generate your first letter above!")
    else:
        for i, record in enumerate(history):
            with st.expander(f"📄 {record.get('type')} — {record.get('candidate_name')} — {record.get('generated_at', '')}", expanded=False):
                col1, col2, col3 = st.columns(3)
                col1.caption(f"**Type:** {record.get('type')}")
                col2.caption(f"**Name:** {record.get('candidate_name')}")
                col3.caption(f"**Role:** {record.get('role', '—')}")

                if record.get("ctc"):
                    st.caption(f"**CTC:** {record.get('ctc')}")
                if record.get("joining_date"):
                    st.caption(f"**Joining Date:** {record.get('joining_date')}")

                dl_col1, dl_col2 = st.columns(2)
                if record.get("docx_path") and os.path.exists(record["docx_path"]):
                    with dl_col1:
                        st.download_button(
                            "⬇️ DOCX",
                            data=read_file_bytes(record["docx_path"]),
                            file_name=f"{record['filename']}.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            key=f"hist_docx_{i}"
                        )
                if record.get("pdf_path") and os.path.exists(record["pdf_path"]):
                    with dl_col2:
                        st.download_button(
                            "⬇️ PDF",
                            data=read_file_bytes(record["pdf_path"]),
                            file_name=f"{record['filename']}.pdf",
                            mime="application/pdf",
                            key=f"hist_pdf_{i}"
                        )
