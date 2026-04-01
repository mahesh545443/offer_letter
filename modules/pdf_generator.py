"""
pdf_generator.py
Analytics Avenue LLP
Fixes:
  - ₹ symbol: assets/ folder fonts committed to repo (Streamlit Cloud compatible)
  - Font re-registration error on Streamlit Cloud fixed
  - Pre-Offer: 2 pages
  - Internship: fully dynamic role/dept based text
"""

import os
from docxtpl import DocxTemplate
from datetime import datetime

BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT  = os.path.dirname(BASE_DIR)
TEMPLATES_DIR = os.path.join(PROJECT_ROOT, "templates")
OUTPUT_DIR    = os.path.join(PROJECT_ROOT, "output")
ASSETS_DIR    = os.path.join(PROJECT_ROOT, "assets")


def ensure_output_dir():
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def render_docx(template_name, context, output_filename):
    ensure_output_dir()
    template_path = os.path.join(TEMPLATES_DIR, template_name)
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"Template not found: {template_path}")
    doc = DocxTemplate(template_path)
    doc.render(context)
    docx_path = os.path.join(OUTPUT_DIR, f"{output_filename}.docx")
    doc.save(docx_path)
    return docx_path


from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image,
    Table, TableStyle, PageBreak, HRFlowable
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import registerFontFamily
from reportlab.pdfgen import canvas


# ── Role → dynamic internship text ───────────────────────────
ROLE_CONTEXT = {
    "Talent Acquisition Intern": {
        "activity": "Talent Acquisition and HR support activities",
        "exposure": "Talent Acquisition processes, recruitment workflow, and basic HR operations",
    },
    "Data Analytics Intern": {
        "activity": "Data Analytics and business intelligence activities",
        "exposure": "data analytics processes, dashboard development, and data-driven reporting",
    },
    "Marketing Intern": {
        "activity": "Digital Marketing and brand development activities",
        "exposure": "digital marketing campaigns, social media management, and market research",
    },
    "Business Development Intern": {
        "activity": "Business Development and client engagement activities",
        "exposure": "business development processes, client engagement, and lead generation",
    },
    "Data Analytics Trainee": {
        "activity": "Data Analytics and business development activities",
        "exposure": "data analytics workflows, reporting, and business development processes",
    },
    "HR Executive": {
        "activity": "Human Resource management and talent operations",
        "exposure": "HR processes, employee lifecycle management, and talent acquisition",
    },
    "Business Analyst": {
        "activity": "Business Analysis and stakeholder coordination activities",
        "exposure": "business analysis processes, requirement gathering, and project coordination",
    },
    "Data Analyst": {
        "activity": "Data Analysis and visualization activities",
        "exposure": "data analysis workflows, visualization tools, and business intelligence reporting",
    },
    "Software Developer": {
        "activity": "Software Development and technical engineering activities",
        "exposure": "software development lifecycle, coding practices, and cross-functional collaboration",
    },
}

def _get_role_context(role: str) -> dict:
    if role in ROLE_CONTEXT:
        return ROLE_CONTEXT[role]
    return {
        "activity": f"{role} activities",
        "exposure": f"{role.lower()} processes and professional work environment",
    }


# ── Font registration — safe for Streamlit Cloud re-runs ─────
def _safe_register(name, path):
    """Register a TTFont — always force fresh registration."""
    try:
        pdfmetrics.registerFont(TTFont(name, path))
    except Exception:
        pass  # ignore all errors including already registered


def _register_fonts():
    """
    Register DejaVuSans for ₹ symbol support.
    System paths checked FIRST — always present on Streamlit Cloud (Ubuntu).
    """
    MATPLOTLIB_FONTS = "/usr/local/lib/python3.12/dist-packages/matplotlib/mpl-data/fonts/ttf"

    def _find(*candidates):
        for p in candidates:
            if p and os.path.exists(p):
                return p
        return None

    # System paths FIRST (guaranteed on Streamlit Cloud Ubuntu & Linux)
    # Assets folder second (for any custom deployment)
    reg  = _find(
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        os.path.join(ASSETS_DIR, "DejaVuSans.ttf"),
        os.path.join(MATPLOTLIB_FONTS, "DejaVuSans.ttf"),
    )
    bold = _find(
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        os.path.join(ASSETS_DIR, "DejaVuSans-Bold.ttf"),
        os.path.join(MATPLOTLIB_FONTS, "DejaVuSans-Bold.ttf"),
    )
    ital = _find(
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf",
        os.path.join(ASSETS_DIR, "DejaVuSans-Oblique.ttf"),
        os.path.join(MATPLOTLIB_FONTS, "DejaVuSans-Oblique.ttf"),
    )
    bi   = _find(
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-BoldOblique.ttf",
        os.path.join(ASSETS_DIR, "DejaVuSans-BoldOblique.ttf"),
        os.path.join(MATPLOTLIB_FONTS, "DejaVuSans-BoldOblique.ttf"),
    )

    if reg and bold:
        try:
            _safe_register("HR",    reg)
            _safe_register("HR-B",  bold)
            _safe_register("HR-I",  ital or reg)
            _safe_register("HR-BI", bi   or bold)
            try:
                registerFontFamily("HR", normal="HR", bold="HR-B",
                                   italic="HR-I", boldItalic="HR-BI")
            except Exception:
                pass
            print(f"[pdf_generator] ✅ Font OK: {reg}")
            return "HR", "HR-B"
        except Exception as e:
            print(f"[pdf_generator] ❌ Font error: {e}")
    else:
        print(f"[pdf_generator] ❌ Font NOT FOUND. reg={reg} bold={bold}")
        print(f"[pdf_generator] ASSETS_DIR={ASSETS_DIR}")
        print(f"[pdf_generator] ASSETS exists={os.path.exists(ASSETS_DIR)}")
        if os.path.exists(ASSETS_DIR):
            print(f"[pdf_generator] ASSETS contents={os.listdir(ASSETS_DIR)}")

    print(f"[pdf_generator] ⚠️ Falling back to Helvetica — ₹ will NOT render")
    return "Helvetica", "Helvetica-Bold"


# Call at module load — but also re-called safely if needed
FR, FB = _register_fonts()

BLACK      = colors.black
WHITE      = colors.white
GRAY       = colors.HexColor("#555555")
LIGHT_GRAY = colors.HexColor("#f5f5f5")
TABLE_HEAD = colors.HexColor("#1F5C99")
TABLE_ALT  = colors.HexColor("#E8F0FE")
BORDER_CLR = colors.HexColor("#2E74B5")

PAGE_W, PAGE_H = A4
LM = 2.0*cm; RM = 2.0*cm; TM = 1.2*cm; BM = 2.0*cm
CW = PAGE_W - LM - RM


class BC(canvas.Canvas):
    def showPage(self):
        self.saveState()
        self.setStrokeColor(BORDER_CLR)
        self.setLineWidth(2)
        m = 3
        self.rect(m, m, PAGE_W - 2*m, PAGE_H - 2*m, stroke=1, fill=0)
        self.restoreState()
        super().showPage()

    def save(self):
        super().save()


class BDT(SimpleDocTemplate):
    def build(self, flowables, **kw):
        kw["canvasmaker"] = BC
        super().build(flowables, **kw)


def S():
    s = getSampleStyleSheet()
    def add(n, **kw):
        if n not in s:
            s.add(ParagraphStyle(name=n, **kw))
    add("B",   fontName=FR, fontSize=10.5, leading=15, textColor=BLACK, alignment=TA_JUSTIFY, spaceAfter=5)
    add("SH",  fontName=FB, fontSize=11,   leading=15, textColor=BLACK, spaceBefore=5, spaceAfter=3)
    add("TIT", fontName=FB, fontSize=14,   leading=18, textColor=BLACK, alignment=TA_CENTER, spaceAfter=8)
    add("SUB", fontName=FB, fontSize=12,   leading=16, textColor=BLACK, alignment=TA_CENTER, spaceAfter=6)
    add("BUL", fontName=FR, fontSize=10.5, leading=14, textColor=BLACK, leftIndent=14, spaceAfter=2)
    add("SUL", fontName=FR, fontSize=10.5, leading=14, textColor=BLACK, leftIndent=28, spaceAfter=1)
    add("SGN", fontName=FB, fontSize=10.5, leading=14, textColor=BLACK, spaceAfter=2)
    add("ITA", fontName=FR, fontSize=10.5, leading=14, textColor=GRAY,  spaceAfter=2)
    return s


def _lh():
    for p in [
        os.path.join(ASSETS_DIR, "letterhead_final.png"),
        os.path.join(ASSETS_DIR, "letterhead.png"),
    ]:
        if os.path.exists(p):
            img = Image(p, width=CW, height=CW*(480/2482))
            img.hAlign = "LEFT"
            return img
    return None


def _sig():
    for p in [
        os.path.join(ASSETS_DIR, "signature_final.png"),
        os.path.join(ASSETS_DIR, "signature.png"),
    ]:
        if os.path.exists(p):
            img = Image(p, width=3.2*cm, height=1.5*cm)
            img.hAlign = "LEFT"
            return img
    return None


def _hdr(title):
    s = S()
    items = []
    lh = _lh()
    if lh:
        items.append(lh)
    else:
        items.append(Paragraph(
            '<font color="#064b86" size="16"><b>Analytics Avenue LLP</b></font>', s["B"]
        ))
    items.append(Spacer(1, 1*mm))
    items.append(Paragraph(title, s["TIT"]))
    items.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey))
    items.append(Spacer(1, 2*mm))
    return items


def _bul(text, s):
    return Paragraph(f"\u2022 {text}", s["BUL"])


def _sub(l, t, s):
    return Paragraph(f"{l}. {t}", s["SUL"])


def _pronoun(salutation):
    if salutation in ["Mr."]:
        return {"sub": "he", "obj": "him", "pos": "his", "cap": "His"}
    return {"sub": "she", "obj": "her", "pos": "her", "cap": "Her"}


def _sig_block(s, company="Analytics Avenue"):
    items = []
    sig = _sig()
    if sig:
        items.append(sig)
    items += [
        Paragraph("<b>For ANALYTICS AVENUE LLP</b>", s["SGN"]),
        Spacer(1, 3*mm),
        Paragraph("<b>Regards,</b>",       s["SGN"]),
        Paragraph("<b>Aswath R</b>",       s["SGN"]),
        Paragraph("<b>Human Resource</b>", s["SGN"]),
        Paragraph(f"<b>{company}</b>",     s["SGN"]),
        Paragraph("<i>(Empower your business with data driven insights)</i>", s["ITA"]),
    ]
    return items


def _doc(pdf_path, compact=False):
    tm = 0.6*cm if compact else TM
    bm = 1.5*cm if compact else BM
    return BDT(
        pdf_path, pagesize=A4,
        leftMargin=LM, rightMargin=RM,
        topMargin=tm, bottomMargin=bm
    )


# ─────────────────────────────────────────────────────────────
# PRE-OFFER LETTER — 2 pages
# ─────────────────────────────────────────────────────────────
def _pre_offer_pdf(ctx, pdf_path):
    global FR, FB
    FR, FB = _register_fonts()  # Always re-register before generating
    s   = S()
    sal = ctx.get("salutation", "Ms.")
    nm  = ctx.get("candidate_name", "")
    rol = ctx.get("role", "")
    doj = ctx.get("joining_date", "")
    stipend   = ctx.get("stipend",   "\u20b910,000")
    incentive = ctx.get("incentive", "\u20b915,000")
    p   = _pronoun(sal)

    doc = _doc(pdf_path)
    st  = []

    # PAGE 1
    st += _hdr("Pre-Offer Letter")
    st.append(Paragraph(
        f'This is to formally acknowledge that <b>{sal} {nm}</b> has been engaged with '
        f'<b>Analytics Avenue LLP</b> in the role of <b>{rol}</b>', s["B"]))
    if training_dur and prob_start:
        st.append(Paragraph(
            f'The candidate will undergo a <b>Training Period of {training_dur}</b> commencing from <b>{doj}</b>, '
            f'followed by a <b>Probationary Period of two to four months</b> starting from <b>{prob_start}</b>.', s["B"]))
    else:
        st.append(Paragraph(
            f'The actual engagement shall commence with a <b>probationary period ranging from '
            f'two to four months</b>, <b>effective from {doj}, the date of joining.</b>', s["B"]))

    st.append(Paragraph("<b>Compensation During Probation</b>", s["SH"]))
    st.append(Paragraph(
        "During the probation period, the candidate will be entitled to the "
        "following compensation:", s["B"]))
    st.append(_bul(f"<b>Fixed Stipend / Base Pay: {stipend} per month</b>", s))
    if incentive:
        st.append(_bul(
            f"<b>Performance-Based Incentive:</b> Up to <b>{incentive} per month</b>, subject "
            "to the successful <b>achievement of assigned targets</b> and <b>performance "
            "benchmarks</b> as defined by the organization.", s))
        st.append(_bul(
            "The performance incentive is variable in nature and will be evaluated based on "
            "internal performance review mechanisms.", s))

    st.append(Paragraph("<b>Confirmation, Promotion &amp; Post-Confirmation Compensation</b>", s["SH"]))
    st.append(Paragraph(
        f'Upon <b>successful completion of the probation period</b> and meeting the prescribed '
        f'performance expectations, <b>{p["sub"]}</b> will be considered for role confirmation '
        f'with an annual compensation structure (CTC) within the range of '
        f'<b>\u20b94 LPA to \u20b96 LPA</b>, comprising:', s["B"]))
    st.append(_bul("Base Pay", s))
    st.append(_bul("Variable / Performance-Based Pay", s))
    st.append(_bul(
        "Applicable Statutory Benefits, including gratuity, as per prevailing laws "
        "and company policy", s))

    # PAGE 2 — compact to fit all content
    from reportlab.lib.styles import ParagraphStyle as PS2
    from reportlab.lib.enums import TA_JUSTIFY as TAJ2
    P2  = PS2(name="P2B",  fontName=FR, fontSize=9.8, leading=13.5, textColor=BLACK, alignment=TAJ2, spaceAfter=4)
    P2S = PS2(name="P2S",  fontName=FR, fontSize=9.8, leading=13,   textColor=BLACK, leftIndent=24, spaceAfter=1)
    from reportlab.platypus import Paragraph as _Pa
    def _s2(l, t): return _Pa(f"{l}. {t}", P2S)

    st.append(PageBreak())
    st += _hdr("Points to Be Noted")
    st.append(Paragraph("<b>1. Promotion &amp; Salary Revision:</b> Employees who meet performance expectations and achieve assigned targets in business development and technical proof-of-concepts (POCs) will be eligible for promotion and a suitable salary hike, as per management discretion. The official salary revision happens during September–October and April–May. Upon successful completion of the Data Analytics Trainee role the employee will be promoted to the role of <b>Business Analyst.</b>", P2))
    st.append(Paragraph("<b>2. Training-Cum-Service Bond:</b> As per the terms of employment, the employee is required to execute a Training-cum-Service Bond committing to serve the company for 12 (twelve) months from the date of joining. If the employee voluntarily resigns or abandons employment before completing this period, they agree to reimburse a proportionate training cost of up to <b>₹1,00,000</b> (Rupees One Lakh only).", P2))
    st.append(Paragraph("<b>3. Roles &amp; Responsibilities:</b> During the tenure, the employee is expected to actively participate in:", P2))
    st.append(_s2("a", "End-to-end business development activities"))
    st.append(_s2("b", "Client engagement and lead generation"))
    st.append(_s2("c", "Follow-ups and achievement of assigned targets"))
    st.append(_s2("d", "Preparation of reports and dashboards"))
    st.append(_s2("e", "Completion of mandatory technical and professional training programs"))
    st.append(Paragraph("<b>4. Performance Management:</b> Repeated performance escalations (more than five (5)) may lead to proportionate salary deductions of <b>₹1,000</b> per instance.", P2))
    st.append(Paragraph("<b>5. Working Hours &amp; Shifts:</b> The employee should be willing to work in any shifts and on weekends, if required, based on business needs.", P2))
    st.append(Paragraph("<b>Notice Period:</b> The company’s official notice period is 90 days. Failure to serve the full notice period may result in the employee being marked as terminated in company.", P2))
    st.append(Spacer(1, 3*mm))
    st += _sig_block(s, "Analytics Avenue")
    st.append(Spacer(1, 2*mm))
    st.append(Paragraph("<b>Acceptance of Offer:</b>", s["SGN"]))
    st.append(Paragraph(f"I, _____________________ accept the position of <b>{rol}</b> at Analytics Avenue under the terms and conditions outlined in this offer letter and the document attached.", P2))
    st.append(Spacer(1, 3*mm))
    st.append(Paragraph("<b>Signature:</b>", s["SGN"]))
    st.append(Spacer(1, 3*mm))
    st.append(Paragraph("<b>Date:</b>", s["SGN"]))

    doc.build(st)


# ─────────────────────────────────────────────────────────────
# INTERNSHIP — fully dynamic by role & department
# ─────────────────────────────────────────────────────────────
def _internship_pdf(ctx, pdf_path):
    global FR, FB
    FR, FB = _register_fonts()  # Always re-register before generating
    s    = S()
    sal  = ctx.get("salutation", "Ms.")
    nm   = ctx.get("intern_name", "")
    reg  = ctx.get("reg_no", "")
    col  = ctx.get("college", "")
    dept = ctx.get("department", "")
    rol  = ctx.get("role", "")
    std  = ctx.get("start_date", "")
    end  = ctx.get("end_date", "")
    dur  = ctx.get("duration", "")
    resp = ctx.get("responsibilities", [])
    p    = _pronoun(sal)

    rc       = _get_role_context(rol)
    activity = rc["activity"]
    exposure = rc["exposure"]

    if col and dept:
        dept_display = dept if dept.lower().startswith("department") else f"Department of {dept}"
        college_line = f"{col}, {dept_display}"
    elif col:
        college_line = col
    elif dept:
        college_line = f"Department of {dept}"
    else:
        college_line = ""

    from reportlab.lib.styles import ParagraphStyle as PS
    from reportlab.lib.enums import TA_JUSTIFY as TAJ, TA_CENTER as TAC
    BC_style   = PS(name="BC2",   fontName=FR, fontSize=10.5, leading=16,
                    textColor=BLACK, alignment=TAJ, spaceAfter=10)
    BSUB_style = PS(name="BSUB2", fontName=FB, fontSize=12,   leading=18,
                    textColor=BLACK, alignment=TAC, spaceAfter=10)

    doc = _doc(pdf_path)
    st  = []

    st += _hdr("Internship Completion Certificate")
    st.append(Paragraph("<b>TO WHOM IT MAY CONCERN</b>", BSUB_style))

    reg_part = f" (Reg. No: <b>{reg}</b>)," if reg else ","
    col_part = f" <b>{college_line}</b>," if college_line else ""
    st.append(Paragraph(
        f"This is to formally certify that <b>{sal} {nm}</b>{reg_part}{col_part} "
        f"has successfully completed {p['pos']} internship with <b>Analytics Avenue LLP</b> "
        f"in the role of <b>{rol}</b>.", BC_style))

    st.append(Paragraph(
        f"{p['cap']} internship was carried out for a period of <b>{dur}</b>, from "
        f"<b>{std}</b> to <b>{end}</b>, during which {p['sub']} was actively "
        f"involved in <b>{activity}</b> under the guidance and supervision of the "
        f"internal team.", BC_style))

    if resp:
        bold_resp = ", ".join(f"<b>{r}</b>" for r in resp)
        st.append(Paragraph(
            f"During the internship tenure, {p['sub']} was engaged in responsibilities "
            f"including {bold_resp}. {p['sub'].capitalize()} demonstrated sincere "
            f"effort, good professional conduct, and a strong willingness to learn throughout "
            f"the internship period.", BC_style))

    st.append(Paragraph(
        f"This internship provided {p['obj']} with practical exposure to "
        f"<b>{exposure}</b> in a professional work environment.", BC_style))

    st.append(Paragraph(
        f"We appreciate {p['pos']} contribution during the internship period and wish "
        f"{p['obj']} success in {p['pos']} future academic and professional endeavors.",
        BC_style))

    st.append(Paragraph(
        "This letter is being issued as an <b>Internship Completion Certificate / Letter of "
        "Completion</b> from <b>Analytics Avenue LLP</b>.", BC_style))

    st.append(Spacer(1, 12*mm))
    st += _sig_block(s, "Analytics Avenue and Advanced Analytics")

    doc.build(st)


# ─────────────────────────────────────────────────────────────
# OFFER LETTER
# ─────────────────────────────────────────────────────────────
def _offer_letter_pdf(ctx, pdf_path):
    global FR, FB
    FR, FB = _register_fonts()  # Always re-register before generating
    s   = S()
    sal = ctx.get("salutation", "Ms.")
    nm  = ctx.get("candidate_name", "")
    rol = ctx.get("role", "")
    dep = ctx.get("department", "")
    doj = ctx.get("joining_date", "")
    ld  = ctx.get("letter_date", "")

    # Dynamic R&R based on role
    role_rr = {
        "Data Analytics Trainee": [
            "Data collection, cleaning, and preprocessing",
            "Building reports and dashboards using Power BI / Excel",
            "End-to-end business development activities",
            "Client engagement and lead generation",
            "Completion of mandatory technical and professional training programs",
        ],
        "Data Analyst": [
            "Data analysis and visualization using Python, SQL, and Power BI",
            "Building and maintaining analytical dashboards",
            "Generating insights from large datasets",
            "Preparing analytical reports for management",
            "Collaborating with cross-functional teams on data projects",
        ],
        "Business Analyst": [
            "Requirement gathering and business process analysis",
            "Preparation of BRD, FRD, and project documentation",
            "Coordination between technical and business teams",
            "Data analysis and reporting for stakeholders",
            "Follow-ups and achievement of assigned targets",
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
    }
    # Use custom R&R if provided (Other role), else use preset
    custom_rr = ctx.get("custom_rr", None)
    if custom_rr:
        rr_items = custom_rr
    else:
        rr_items = role_rr.get(rol, [
            "End-to-end business development activities",
            "Client engagement and lead generation",
            "Follow-ups and achievement of assigned targets",
            "Preparation of reports and dashboards",
            "Completion of mandatory technical and professional training programs",
        ])

    doc = _doc(pdf_path)
    st  = []

    st += _hdr("Offer Letter")
    st.append(Paragraph(f"Date: <b>{ld}</b>", s["B"]))
    st.append(Spacer(1, 2*mm))
    st.append(Paragraph(f"Dear <b>{sal} {nm}</b>,", s["B"]))
    st.append(Paragraph(
        f"We are pleased to extend this offer of employment to you for the position of "
        f"<b>{rol}</b> in the <b>{dep}</b> department at <b>Analytics Avenue LLP</b>. "
        f"Your employment will commence from <b>{doj}</b>.", s["B"]))

    st.append(Paragraph("<b>Compensation &amp; Benefits</b>", s["SH"]))
    st.append(Paragraph(
        f"Your total Cost to Company (CTC) is <b>{ctx.get('ctc_lpa', '')} "
        f"({ctx.get('ctc_annual_str', '')} per annum)</b>, structured as follows:", s["B"]))

    tdata = [
        ["Salary Component",                  "Monthly Amount"],
        ["Basic Salary",                      ctx.get("basic_monthly_str", "")],
        ["House Rent Allowance (HRA)",        ctx.get("hra_monthly_str", "")],
        ["Provident Fund \u2014 Employer",    ctx.get("pf_monthly_str", "")],
        ["Special Allowance",                 ctx.get("special_allowance_monthly_str", "")],
        ["Gross Monthly (Fixed)",             ctx.get("gross_monthly_str", "")],
        ["Variable Pay (Annual, Perf-Based)", ctx.get("variable_annual_str", "")],
        ["Total CTC (Annual)",                ctx.get("ctc_annual_str", "")],
    ]
    cw  = [CW*0.70, CW*0.30]
    tbl = Table(tdata, colWidths=cw)
    tbl.setStyle(TableStyle([
        ("BACKGROUND",     (0,0),(-1,0),  TABLE_HEAD),
        ("TEXTCOLOR",      (0,0),(-1,0),  WHITE),
        ("FONTNAME",       (0,0),(-1,0),  FB),
        ("FONTNAME",       (0,1),(-1,-1), FR),
        ("FONTSIZE",       (0,0),(-1,-1), 10),
        ("ROWBACKGROUNDS", (0,1),(-1,-1), [WHITE, LIGHT_GRAY]),
        ("BACKGROUND",     (0,5),(-1,5),  TABLE_ALT),
        ("BACKGROUND",     (0,7),(-1,7),  TABLE_ALT),
        ("FONTNAME",       (0,5),(-1,5),  FB),
        ("FONTNAME",       (0,7),(-1,7),  FB),
        ("ALIGN",          (1,0),(1,-1),  "RIGHT"),
        ("VALIGN",         (0,0),(-1,-1), "MIDDLE"),
        ("TOPPADDING",     (0,0),(-1,-1), 5),
        ("BOTTOMPADDING",  (0,0),(-1,-1), 5),
        ("LEFTPADDING",    (0,0),(-1,-1), 8),
        ("RIGHTPADDING",   (0,0),(-1,-1), 8),
        ("GRID",           (0,0),(-1,-1), 0.5, colors.HexColor("#CCCCCC")),
    ]))
    st.append(tbl)
    st.append(Spacer(1, 3*mm))
    st.append(Paragraph("<b>Terms &amp; Conditions</b>", s["SH"]))
    st.append(_bul("<b>Notice Period:</b> 90 days from either side after confirmation.", s))
    st.append(_bul(f"<b>Training Bond:</b> 12 months. Early exit attracts recovery of up to <b>\u20b91,00,000</b>.", s))
    st.append(_bul("<b>Background Verification:</b> Offer subject to successful background verification.", s))
    st.append(_bul("<b>Performance Management:</b> Repeated escalations (more than 5) may lead to proportionate salary deductions of <b>₹1,000</b> per instance.", s))
    st.append(_bul("<b>Working Hours &amp; Shifts:</b> The employee should be willing to work in any shifts and on weekends, if required, based on business needs.", s))

    # Add R&R on page 1 to fill the gap
    st.append(Spacer(1, 3*mm))
    st.append(Paragraph("<b>Roles &amp; Responsibilities</b>", s["SH"]))
    st.append(Paragraph("During the tenure, the employee is expected to actively participate in:", s["B"]))
    for item in rr_items:
        st.append(_bul(item, s))

    # Page 2 — closing, signature, acceptance
    st.append(PageBreak())
    st += _hdr("Offer Letter")
    st.append(Paragraph(
        "We look forward to welcoming you to the Analytics Avenue LLP family. Please sign "
        "and return a copy of this letter as confirmation of your acceptance.", s["B"]))
    st.append(Spacer(1, 8*mm))
    st += _sig_block(s, "Analytics Avenue LLP")
    st.append(Spacer(1, 6*mm))
    st.append(Paragraph("<b>Acceptance of Offer:</b>", s["SGN"]))
    st.append(Paragraph(
        f"I, _____________________ accept the offer of employment as <b>{rol}</b> at "
        "Analytics Avenue LLP under the terms and conditions outlined in this offer letter.",
        s["B"]))
    st.append(Spacer(1, 6*mm))
    st.append(Paragraph("<b>Signature:</b>", s["SGN"]))
    st.append(Spacer(1, 6*mm))
    st.append(Paragraph("<b>Date:</b>", s["SGN"]))

    doc.build(st)


# ─────────────────────────────────────────────────────────────
# ENTRY POINTS
# ─────────────────────────────────────────────────────────────
def generate_pdf_direct(doc_type_key, context, pdf_path):
    try:
        if   doc_type_key == "pre_offer":    _pre_offer_pdf(context, pdf_path)
        elif doc_type_key == "internship":   _internship_pdf(context, pdf_path)
        elif doc_type_key == "offer_letter": _offer_letter_pdf(context, pdf_path)
        return os.path.exists(pdf_path)
    except Exception as e:
        print(f"PDF error: {e}")
        import traceback; traceback.print_exc()
        return False


def generate_document(template_name, context, candidate_name, doc_type):
    ensure_output_dir()
    date_str  = datetime.now().strftime("%d%m%Y")
    safe_name = candidate_name.replace(" ", "_").replace(".", "")
    filename  = f"{safe_name}_{doc_type}_{date_str}"
    type_map  = {
        "PreOffer":    "pre_offer",
        "Internship":  "internship",
        "OfferLetter": "offer_letter",
    }
    pdf_key = type_map.get(doc_type, "pre_offer")
    try:
        docx_path = render_docx(template_name, context, filename)
        pdf_path  = os.path.join(OUTPUT_DIR, f"{filename}.pdf")
        pdf_ok    = generate_pdf_direct(pdf_key, context, pdf_path)
        return {
            "docx_path": docx_path,
            "pdf_path":  pdf_path if pdf_ok else None,
            "filename":  filename,
            "success":   True,
            "error":     None,
        }
    except Exception as e:
        return {
            "docx_path": None,
            "pdf_path":  None,
            "filename":  filename,
            "success":   False,
            "error":     str(e),
        }


def read_file_bytes(path):
    with open(path, "rb") as f:
        return f.read()
