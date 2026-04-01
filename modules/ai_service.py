"""
ai_service.py
Analytics Avenue LLP
Groq performs ALL salary math — fully dynamic, any prompt format.
"""

import os
import json
import re
from dotenv import load_dotenv

load_dotenv()


def _get_groq_key() -> str:
    try:
        import streamlit as st
        key = st.secrets.get("GROQ_API_KEY", "")
        if key:
            return key
    except Exception:
        pass
    return os.getenv("GROQ_API_KEY", "")


def get_groq_client():
    try:
        from groq import Groq
        key = _get_groq_key()
        if not key:
            return None
        return Groq(api_key=key)
    except Exception:
        return None


def parse_prompt(prompt_text: str) -> dict:
    client = get_groq_client()
    system_prompt = """You are an HR data extractor for Analytics Avenue LLP.
Extract structured data from HR letter generation prompts.
Return ONLY valid JSON, no explanation, no markdown.

JSON structure:
{
  "document_type": "pre_offer" or "offer_letter" or "internship",
  "candidate_name": "full name or null",
  "role": "job role or null",
  "ctc_lpa": numeric value like 6.0 or null,
  "duration_months": numeric or null,
  "joining_date": "date string or null",
  "salary_notes": "any extra salary instructions or null"
}"""
    if client:
        try:
            response = client.chat.completions.create(
                model="llama3-8b-8192",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": prompt_text}
                ],
                temperature=0.1, max_tokens=300,
            )
            raw = response.choices[0].message.content.strip()
            raw = re.sub(r"```json|```", "", raw).strip()
            return json.loads(raw)
        except Exception as e:
            print(f"Groq parse error: {e}")
    return _fallback_parse(prompt_text)


def parse_salary_prompt_groq(prompt_text: str, model: str = "llama3-8b-8192") -> dict:
    """
    HR types ANY salary description — Groq calculates everything.
    Handles: %, amounts in LPA, amounts in rupees, PF on CTC/basic/70%CTC, anything.
    """
    client = get_groq_client()

    system_prompt = """You are a precise salary calculator for an Indian company HR system.
HR will describe a salary in ANY format. You MUST calculate and return exact rupee amounts.

=== STEP 1: EXTRACT CTC ===
- "5 LPA" / "5 lakhs" / "5L" = 500000 rupees/year
- "6.5 LPA" = 650000 rupees/year
- "40000/month" = 480000 rupees/year
- "CTC 8 lakh" = 800000 rupees/year

=== STEP 2: CALCULATE EACH COMPONENT ===
HR may give amounts OR percentages — handle BOTH:

CRITICAL RULE FOR BASIC:
- If a number < 20 appears near "base/basic" WITHOUT "%" or "lpa" → it means LPA amount
  Example: "5lpa 4 base" → CTC=500000, basic=4 LPA=400000
  Example: "6lpa 3.5 base" → CTC=600000, basic=3.5 LPA=350000
  Example: "8lpa basic 4.5" → CTC=800000, basic=4.5 LPA=450000
- If a number has "%" after it → it means percentage of CTC
  Example: "40% basic" → basic = CTC × 0.40
- If a number has "lpa" → it means rupee amount
  Example: "basic 3.8 lpa" → basic = 380000

BASIC:
- "basic 40%" or "40% base" → basic_annual = CTC × 0.40
- "basic 3.8 LPA" or "3.8 as base" or "base is 3.8" → basic_annual = 380000
- "4 base" or "base 4" or "4 basic" (no % sign) → basic_annual = 4 LPA = 400000
- "basic 30000/month" → basic_annual = 360000
- "basic 50% of CTC" → basic_annual = CTC × 0.50

HRA:
- "HRA 20% of basic" → hra_annual = basic_annual × 0.20
- "HRA 50% of basic" → hra_annual = basic_annual × 0.50
- "HRA 10% of CTC" → hra_annual = CTC × 0.10
- "HRA 5000/month" → hra_annual = 60000
- If HRA not mentioned → default = basic_annual × 0.20

PF:
- "PF 12% of basic" → pf_annual = basic_annual × 0.12
- "PF 12% of 70% of CTC" → pf_annual = (CTC × 0.70) × 0.12
- "PF 10% on 70% CTC" → pf_annual = (CTC × 0.70) × 0.10
- "deducting 10% on PF towards 70% of CTC" → pf_annual = (CTC × 0.70) × 0.10
- "PF 12% on 60% CTC" → pf_annual = (CTC × 0.60) × 0.12
- "PF 780/month" → pf_annual = 9360
- "PF statutory ceiling" → pf_annual = 15000 × 0.12 × 12 = 21600
- "no PF" / "PF opted out" / "without PF" → pf_annual = 0
- If PF not mentioned → default = basic_annual × 0.12

VARIABLE:
- "variable 10%" or "10% variable" → variable_annual = CTC × 0.10
- "variable 1.2 LPA" or "1.2 as variable" → variable_annual = 120000
- "bonus 50000" → variable_annual = 50000
- "no variable" / "no bonus" → variable_annual = 0
- If variable not mentioned → default = 0

=== STEP 3: COMPUTE SPECIAL ALLOWANCE ===
special_allowance_annual = CTC - basic_annual - hra_annual - pf_annual - variable_annual
(Must be >= 0. If negative, reduce pf_annual first, then hra_annual.)

=== STEP 4: RETURN JSON ===
Return ONLY this JSON, no text before or after:
{
  "ctc_annual": <integer rupees>,
  "basic_monthly": <integer = basic_annual/12 rounded>,
  "hra_monthly": <integer = hra_annual/12 rounded>,
  "pf_monthly": <integer = pf_annual/12 rounded>,
  "special_allowance_monthly": <integer = special_allowance_annual/12 rounded>,
  "gross_monthly": <integer = basic+hra+pf+special monthly>,
  "variable_annual": <integer>,
  "pf_opted": <true if pf_monthly > 0 else false>,
  "ctc_lpa": "<X.X LPA>"
}

VERIFY before returning: (gross_monthly × 12) + variable_annual = ctc_annual (allow ±24 rounding)"""

    if client:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": prompt_text}
                ],
                temperature=0.0,
                max_tokens=400,
            )
            raw = response.choices[0].message.content.strip()
            raw = re.sub(r"```json|```", "", raw).strip()
            # Extract JSON if there's any surrounding text
            json_match = re.search(r'\{[\s\S]*\}', raw)
            if json_match:
                raw = json_match.group()
            result = json.loads(raw)

            # Binary overrides for explicit no-PF / no-variable
            p_lower = prompt_text.lower()
            NO_PF = ["no pf","pf no","without pf","pf opted out","opt out pf",
                     "pf 0","0% pf","no provident","pf not applicable","no epf"]
            NO_VAR = ["no variable","no bonus","no incentive","without variable",
                      "0% variable","variable 0","fixed only","no performance"]
            if any(pat in p_lower for pat in NO_PF):
                result["pf_monthly"] = 0
                result["pf_opted"]   = False
            if any(pat in p_lower for pat in NO_VAR):
                result["variable_annual"] = 0

            return _validate_computed_salary(result)

        except Exception as e:
            print(f"Groq salary parse error: {e}")

    return _fallback_salary_parse(prompt_text)


def _validate_computed_salary(r: dict) -> dict:
    """
    Light validation — trust Groq's numbers, only fix obvious errors.
    Do NOT override valid values with wrong defaults.
    """
    from modules.salary_calc import format_inr

    ctc        = int(float(r.get("ctc_annual", 600000) or 600000))
    basic_m    = int(float(r.get("basic_monthly", 0) or 0))
    hra_m      = int(float(r.get("hra_monthly", 0) or 0))
    pf_m       = int(float(r.get("pf_monthly", 0) or 0))
    variable_a = int(float(r.get("variable_annual", 0) or 0))
    pf_opted   = bool(r.get("pf_opted", pf_m > 0))

    # CTC sanity — if LLM returned LPA instead of rupees
    if ctc <= 50:
        ctc = int(ctc * 100000)
    elif ctc < 10000:
        ctc = int(ctc * 10000)

    ctc_monthly = ctc / 12

    # Basic sanity — only fix if completely wrong (< 10% or > 90% of CTC monthly)
    if basic_m <= 0 or basic_m > ctc_monthly * 0.90:
        basic_m = int(ctc_monthly * 0.40)

    # HRA — only fix if negative or zero (don't override valid values)
    if hra_m < 0:
        hra_m = 0

    # PF
    if not pf_opted:
        pf_m = 0
    if pf_m < 0:
        pf_m = 0

    # Variable
    if variable_a < 0:
        variable_a = 0

    # Recompute special allowance to ensure CTC reconciles exactly
    known_annual   = (basic_m + hra_m + pf_m) * 12 + variable_a
    special_annual = ctc - known_annual

    # If negative, PF and HRA come FROM basic (not additional to it)
    # Reduce basic accordingly, keep PF and HRA intact
    if special_annual < 0:
        excess = -special_annual
        # First try: reduce basic to absorb excess (PF/HRA come from within basic)
        basic_reduce = min(basic_m * 12, excess)
        basic_m = int((basic_m * 12 - basic_reduce) / 12)
        special_annual = ctc - (basic_m + hra_m + pf_m) * 12 - variable_a
        # If still negative (very edge case), then reduce pf
        if special_annual < 0:
            excess2 = -special_annual
            pf_m = max(0, pf_m - int(excess2 / 12) - 1)
            special_annual = ctc - (basic_m + hra_m + pf_m) * 12 - variable_a
        if special_annual < 0:
            special_annual = 0

    special_m = int(special_annual / 12)
    # Cap tiny special amounts (< ₹100) — rounding artifacts, absorb into basic
    if 0 < special_m < 100:
        basic_m += special_m
        special_m = 0
        special_annual = 0
    elif special_m < 0:
        special_m = 0
        special_annual = 0
    gross_m = basic_m + hra_m + pf_m + special_m

    return {
        "ctc_annual":                ctc,
        "basic_annual":              basic_m * 12,
        "hra_annual":                hra_m * 12,
        "pf_annual":                 pf_m * 12,
        "special_allowance_annual":  special_annual,
        "variable_annual":           variable_a,
        "basic_monthly":             basic_m,
        "hra_monthly":               hra_m,
        "pf_monthly":                pf_m,
        "special_allowance_monthly": special_m,
        "gross_monthly":             gross_m,
        "ctc_annual_str":                format_inr(ctc),
        "basic_monthly_str":             format_inr(basic_m),
        "hra_monthly_str":               format_inr(hra_m),
        "pf_monthly_str":                format_inr(pf_m) if pf_m > 0 else "N/A",
        "special_allowance_monthly_str": format_inr(special_m),
        "variable_annual_str":           format_inr(variable_a),
        "gross_monthly_str":             format_inr(gross_m),
        "ctc_lpa":        r.get("ctc_lpa", f"{ctc/100000:.1f} LPA"),
        "pf_opted":       pf_m > 0,
        "pf_percent":     round(pf_m * 12 / (basic_m * 12) * 100, 1) if basic_m > 0 and pf_m > 0 else 0,
        "base_percent":   round(basic_m * 12 / ctc * 100, 1),
        "hra_percent":    round(hra_m / basic_m * 100, 1) if basic_m > 0 else 0.0,
        "variable_percent": round(variable_a / ctc * 100, 1),
    }


def _fallback_salary_parse(prompt_text: str) -> dict:
    """Rule-based fallback when Groq unavailable. Handles any format."""
    p = prompt_text.lower().strip()
    p = re.sub(r'[,;/]+', ' ', p)
    # Normalize "percent" / "per cent" → "%"
    p = re.sub(r'\bper\s*cent\b|\bpercent\b|\bpercnt\b|\bperrcent\b', '%', p)
    # Normalize common typos for salary keywords
    p = re.sub(r'\bvarib(?:a|e)le\b|\bvariab(?:e|al)\b|\bvaribal\b', 'variable', p)
    p = re.sub(r'\bbonous\b|\bbonus\b', 'bonus', p)
    p = re.sub(r'\bbasic\b|\bbasik\b|\bbasci\b', 'basic', p)
    p = re.sub(r'\s+', ' ', p).strip()

    # ── CTC ──────────────────────────────────────────────────
    ctc = 600000.0
    m = re.search(r'ctc\s+(?:of\s+)?(\d+\.?\d*)\s*(?:lpa|lakh|l\b)', p)
    if not m:
        m = re.search(r'(\d+\.?\d*)\s*(?:lpa|lakh|l\b)', p)
    if m:
        ctc = float(m.group(1)) * 100000
    else:
        m = re.search(r'(\d+\.?\d*)\s*k?\s*(?:monthly|per\s*month|pm\b)', p)
        if m:
            val = float(m.group(1))
            ctc = (val * 1000 if val < 1000 else val) * 12

    # ── BASIC ─────────────────────────────────────────────────
    basic_a = ctc * 0.40  # default 40%

    # Priority order for basic extraction:
    # 1. "3.8 as a base" / "3.8 as base"
    m = re.search(r'(\d+\.?\d*)\s+as\s+(?:a\s+|an\s+|the\s+)?base(?:\s+pay)?', p)
    if m:
        basic_a = float(m.group(1)) * 100000
    else:
        # 2. "basic 3.8 lpa" / "base 4 lpa" (keyword THEN amount — higher priority)
        m = re.search(r'bas(?:e|ic)(?:\s+pay)?\s+(\d+\.?\d*)\s*lpa?', p)
        if m:
            basic_a = float(m.group(1)) * 100000
        else:
            # 3. "4lpa base" (amount lpa THEN keyword — only if != CTC)
            m = re.search(r'(\d+\.?\d*)\s*lpa?\s*(?:as\s+(?:a\s+)?)?bas(?:e|ic)', p)
            if m and abs(float(m.group(1)) * 100000 - ctc) > 1000:
                basic_a = float(m.group(1)) * 100000
            else:
                # 4. Bare number near base: "4 base" / "base 4" (no % or lpa) → LPA amount
                # Use word boundary to avoid matching partial numbers
                m = re.search(r'(\d+\.?\d*)\b\s+bas(?:e|ic)\b(?!\s*%|lpa)', p)
                if not m:
                    m = re.search(r'bas(?:e|ic)(?:\s+pay)?\s+(\d+\.?\d*)\b(?!\s*%|\s*lpa)', p)
                if m:
                    val = float(m.group(1))
                    if 0.5 < val < 30:  # bare number 0.5-30 = LPA amount
                        basic_a = val * 100000
                else:
                    # 5. "40% basic" / "basic 40%" — stop before pf/variable keywords
                    m = re.search(r'(\d+\.?\d*)\s*%\s*bas(?:e|ic)', p)
                    if not m:
                        # Look for % immediately after base keyword (within 5 chars)
                        m = re.search(r'bas(?:e|ic)(?:\s+pay)?\s{0,5}(\d+\.?\d*)\s*%', p)
                    if m:
                        basic_a = ctc * float(m.group(1)) / 100

    # ── HRA ───────────────────────────────────────────────────
    hra_a = basic_a * 0.20  # default 20% of basic
    m = re.search(r'(\d+\.?\d*)\s*%\s*hra', p)
    if not m:
        m = re.search(r'hra\s*[^\d]*(\d+\.?\d*)\s*%', p)
    if m:
        hra_a = basic_a * float(m.group(1)) / 100

    # ── NO-PF check ───────────────────────────────────────────
    no_pf = bool(re.search(
        r'no\s*pf|pf\s*no|without\s*pf|pf\s*opt|\bpf\s*0\b|pf\s*not', p))

    # ── PF ────────────────────────────────────────────────────
    pf_a = basic_a * 0.12  # default
    if no_pf:
        pf_a = 0.0
    else:
        # "10% on PF towards 70% of CTC" / "PF 10% of 70% of CTC"
        m = re.search(r'(\d+\.?\d*)\s*%[^%\d]*(\d+\.?\d*)\s*%[^%]*?ctc', p)
        if m:
            pf_rate   = float(m.group(1)) / 100
            ctc_base  = float(m.group(2)) / 100
            pf_a = ctc * ctc_base * pf_rate
        else:
            # "PF 12% of basic" / "12% pf"
            m = re.search(r'(\d+\.?\d*)\s*%\s*pf', p)
            if not m:
                m = re.search(r'pf\s*[^\d]*(\d+\.?\d*)\s*%', p)
            if m:
                pf_a = basic_a * float(m.group(1)) / 100

    # ── NO-VARIABLE check ─────────────────────────────────────
    no_var = bool(re.search(r'no\s*(?:variable|bonus|incentive)', p))

    # ── VARIABLE ──────────────────────────────────────────────
    var_a = 0.0
    if not no_var:
        # "1.2 as a variable pay" / "1.2 as variable"
        m = re.search(r'(\d+\.?\d*)\s+as\s+(?:a\s+|an\s+)?variable(?:\s+pay)?', p)
        if m:
            var_a = float(m.group(1)) * 100000
        else:
            # "variable 1.2 lpa" / "variable pay 1.2"
            m = re.search(r'variable(?:\s+pay)?\s+(\d+\.?\d*)\s*lpa?', p)
            if m:
                var_a = float(m.group(1)) * 100000
            else:
                # "10% variable" / "variable 10%"
                m = re.search(r'(\d+\.?\d*)\s*%\s*(?:variable|bonus|incentive)', p)
                if not m:
                    m = re.search(r'(?:variable|bonus|incentive)(?:\s+pay)?\s*[^\d]*(\d+\.?\d*)\s*%', p)
                if m:
                    var_a = ctc * float(m.group(1)) / 100

    # ── SPECIAL ALLOWANCE (remainder) ─────────────────────────
    special_a = ctc - basic_a - hra_a - pf_a - var_a
    if special_a < 0:
        excess = -special_a
        # Reduce HRA first (it's a default, not explicitly set by HR)
        hra_cut = min(hra_a, excess); hra_a -= hra_cut; excess -= hra_cut
        # Then reduce basic (PF and variable stay intact — explicitly requested)
        if excess > 0:
            basic_cut = min(basic_a - 1, excess); basic_a -= basic_cut; excess -= basic_cut
        special_a = max(0, ctc - basic_a - hra_a - pf_a - var_a)

    return _validate_computed_salary({
        "ctc_annual":      int(ctc),
        "basic_monthly":   round(basic_a / 12),
        "hra_monthly":     round(hra_a / 12),
        "pf_monthly":      round(pf_a / 12),
        "variable_annual": round(var_a),
        "pf_opted":        pf_a > 0,
        "ctc_lpa":         f"{ctc/100000:.1f} LPA",
    })

def _fallback_parse(prompt_text: str) -> dict:
    p = prompt_text.lower()
    if any(x in p for x in ["pre-offer", "pre offer", "preoffer"]):
        doc_type = "pre_offer"
    elif any(x in p for x in ["offer letter", "offer"]):
        doc_type = "offer_letter"
    elif any(x in p for x in ["internship", "intern"]):
        doc_type = "internship"
    else:
        doc_type = "pre_offer"
    name_match = re.search(r'for\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)', prompt_text)
    ctc_match  = re.search(r'(\d+\.?\d*)\s*lpa', p)
    dur_match  = re.search(r'(\d+)\s*month', p)
    role_match = re.search(r'[–\-]\s*([A-Za-z\s]+?)(?:\s*[–\-]|$)', prompt_text)
    return {
        "document_type":   doc_type,
        "candidate_name":  name_match.group(1) if name_match else None,
        "role":            role_match.group(1).strip() if role_match else None,
        "ctc_lpa":         float(ctc_match.group(1)) if ctc_match else None,
        "duration_months": int(dur_match.group(1)) if dur_match else None,
        "joining_date":    None,
        "salary_notes":    None,
    }


# ── Responsibility & Role helpers ────────────────────────────


import re

# ── Common spelling corrections for HR responsibilities ───────
SPELL_FIXES = {
    # Tech terms
    r'\blms\b': 'LMS', r'\bcrm\b': 'CRM', r'\berp\b': 'ERP',
    r'\bapi\b': 'API', r'\bapis\b': 'APIs', r'\bui\b': 'UI', r'\bux\b': 'UX',
    r'\bsql\b': 'SQL', r'\bhtml\b': 'HTML', r'\bcss\b': 'CSS',
    r'\bpython\b': 'Python', r'\bjava\b': 'Java', r'\breact\b': 'React',
    r'\bnode\b': 'Node', r'\bmysql\b': 'MySQL', r'\bmongodb\b': 'MongoDB',
    r'\bpower\s*bi\b': 'Power BI', r'\bpowerbi\b': 'Power BI',
    r'\bms\s*excel\b': 'MS Excel', r'\bexcel\b': 'Excel',
    r'\bmicrosoft\b': 'Microsoft', r'\bgoogle\b': 'Google',
    r'\bai\b': 'AI', r'\bml\b': 'ML', # r'\bit\b': 'IT',  # disabled - too aggressive, replaces common word 'it' r'\bhr\b': 'HR',
    r'\bkpi\b': 'KPI', r'\bkpis\b': 'KPIs', r'\bseo\b': 'SEO',
    r'\bsmo\b': 'SMO', r'\bpoc\b': 'POC', r'\bpocs\b': 'POCs',
    # Common misspellings
    r'\besign\b': 'design',  # "esign" → "design"
    r'\bdesing\b': 'design',
    r'\bdevlop\b': 'develop', r'\bdevelope\b': 'develop',
    r'\bdeveloer\b': 'developer', r'\bdevelpoer\b': 'developer',
    r'\bmanaer\b': 'manager', r'\bmanageer\b': 'manager',
    r'\banalst\b': 'analyst', r'\banalyist\b': 'analyst',
    r'\bsciene\b': 'science', r'\bscienece\b': 'science',
    r'\benginer\b': 'engineer', r'\bengineer\b': 'engineer',
    r'\brecuiter\b': 'recruiter', r'\brecrutier\b': 'recruiter',
    r'\bdesiner\b': 'designer', r'\bdesigener\b': 'designer',
    r'\bscalabe\b': 'scalable', r'\bscaleable\b': 'scalable',
    r'\bscalabale\b': 'scalable', r'\bscalabal\b': 'scalable',
    r'\bbuid\b': 'build', r'\bbuld\b': 'build', r'\bbiuld\b': 'build',
    r'\bcient\b': 'client', r'\bclinet\b': 'client', r'\bcleint\b': 'client',
    r'\brequirment\b': 'requirement', r'\brequirements\b': 'requirements',
    r'\bapllication\b': 'application', r'\bapplication\b': 'application',
    r'\bdeveloment\b': 'development', r'\bdevelepment\b': 'development',
    r'\bmanagment\b': 'management', r'\bmanagement\b': 'management',
    r'\bimplmentation\b': 'implementation', r'\bimplementation\b': 'implementation',
    r'\bcolaborate\b': 'collaborate', r'\bcollabrate\b': 'collaborate',
    r'\banalitcs\b': 'analytics', r'\banaltics\b': 'analytics',
    r'\bdashbord\b': 'dashboard', r'\bdashbaord\b': 'dashboard',
    r'\breprot\b': 'report', r'\breport\b': 'report',
    r'\bstakholders\b': 'stakeholders', r'\bstakeholders\b': 'stakeholders',
    r'\bcoordiantion\b': 'coordination', r'\bcoordination\b': 'coordination',
    r'\bdocumentaion\b': 'documentation', r'\bdocumentation\b': 'documentation',
    r'\bintegartion\b': 'integration', r'\bintegration\b': 'integration',
    r'\bmaintanance\b': 'maintenance', r'\bmaintenance\b': 'maintenance',
    r'\boptimzation\b': 'optimization', r'\boptimization\b': 'optimization',
    r'\bperformace\b': 'performance', r'\bperformance\b': 'performance',
    r'\btechnial\b': 'technical', r'\btechinical\b': 'technical',
    r'\bbuisness\b': 'business', r'\bbussiness\b': 'business',
    r'\brendering\b': 'rendering', r'\bfuntionality\b': 'functionality',
    r'\bfunctionality\b': 'functionality', r'\bwebapp\b': 'web application',
    r'\bwebsite\b': 'website', r'\bend.to.end\b': 'end-to-end',
    r'\bend to end\b': 'end-to-end',
}

# ── Role-based default responsibilities ───────────────────────
ROLE_DEFAULTS = {
    "Data Analyst": [
        "Collect, clean, and preprocess data from multiple sources.",
        "Build and maintain analytical dashboards using Power BI or Excel.",
        "Generate actionable insights from large datasets for management.",
        "Prepare and present analytical reports to stakeholders.",
        "Collaborate with cross-functional teams on data-driven projects.",
    ],
    "Data Analytics Trainee": [
        "Support data collection, cleaning, and preprocessing tasks.",
        "Assist in building reports and dashboards using Power BI and Excel.",
        "Participate in business development and client engagement activities.",
        "Complete mandatory technical and professional training programs.",
        "Follow up on assigned targets and report progress to the team.",
    ],
    "Business Analyst": [
        "Gather and document business requirements from stakeholders.",
        "Prepare Business Requirement Documents (BRD) and Functional Requirement Documents (FRD).",
        "Coordinate between technical and business teams for project delivery.",
        "Conduct data analysis and prepare reports for management review.",
        "Identify process gaps and recommend improvements.",
    ],
    "Software Developer": [
        "Design, develop, and maintain scalable software applications.",
        "Write clean, well-documented, and testable code.",
        "Collaborate with product and design teams on feature development.",
        "Debug and resolve software defects and performance issues.",
        "Participate in code reviews and technical discussions.",
    ],
    "HR Executive": [
        "Manage end-to-end recruitment and talent acquisition processes.",
        "Coordinate onboarding and induction programs for new employees.",
        "Maintain accurate employee records and HR documentation.",
        "Handle employee queries and support HR operations.",
        "Coordinate performance management and appraisal activities.",
    ],
    "Talent Acquisition Intern": [
        "Assist in sourcing and screening candidates for open positions.",
        "Schedule interviews and coordinate with candidates and hiring managers.",
        "Maintain recruitment trackers and update candidate status regularly.",
        "Support onboarding documentation and joining formalities.",
        "Assist in drafting job descriptions and posting on job portals.",
    ],
    "Data Analytics Intern": [
        "Assist in data collection, cleaning, and preprocessing tasks.",
        "Support dashboard creation using Power BI or Excel.",
        "Analyze datasets and summarize findings for the team.",
        "Prepare basic analytical reports under supervisor guidance.",
        "Participate in team meetings and contribute to ongoing projects.",
    ],
    "Marketing Intern": [
        "Support digital marketing campaigns across social media platforms.",
        "Assist in content creation, scheduling, and performance tracking.",
        "Conduct market research and compile competitor analysis reports.",
        "Coordinate with design teams for creatives and marketing materials.",
        "Track and report campaign metrics and engagement data.",
    ],
    "Business Development Intern": [
        "Identify and research potential clients and business opportunities.",
        "Support lead generation and initial client outreach activities.",
        "Assist in preparing proposals, presentations, and pitch decks.",
        "Follow up with prospects and maintain the CRM database.",
        "Coordinate with internal teams for client requirements and delivery.",
    ],
}

GENERIC_DEFAULTS = [
    "Actively participate in assigned projects and deliver quality outcomes.",
    "Collaborate with team members and contribute to organizational goals.",
    "Prepare regular progress reports and update stakeholders.",
    "Adhere to company policies, timelines, and professional standards.",
    "Continuously upskill through training programs and self-learning.",
]


def fix_spelling(text: str) -> str:
    """Apply spelling corrections to a line of text."""
    for pattern, replacement in SPELL_FIXES.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text


def fix_responsibility_line(line: str) -> str:
    """Fix a single responsibility line — spelling, grammar, capitalization, punctuation."""
    line = line.strip()
    if not line:
        return line
    # Remove leading bullet/dash/number
    line = re.sub(r'^[\•\-\*\d\.]+\s*', '', line).strip()
    # Fix spelling
    line = fix_spelling(line)
    # Sentence case
    if line:
        line = line[0].upper() + line[1:]
    # Fix comma spacing
    line = re.sub(r'\s*,\s*', ', ', line)
    # Add period if missing
    if line and line[-1] not in '.!?,;':
        line += '.'
    return line


def complete_responsibilities(lines: list, role: str, min_points: int = 5) -> list:
    """
    If fewer than min_points given, auto-add relevant points based on role.
    Returns completed list of responsibilities.
    """
    fixed = [fix_responsibility_line(l) for l in lines if l.strip()]

    if len(fixed) >= min_points:
        return fixed

    # Get defaults for role
    role_key = None
    for key in ROLE_DEFAULTS:
        if key.lower() in role.lower() or role.lower() in key.lower():
            role_key = key
            break

    defaults = ROLE_DEFAULTS.get(role_key, GENERIC_DEFAULTS) if role_key else GENERIC_DEFAULTS

    # Add defaults that are not already covered
    existing_text = ' '.join(fixed).lower()
    for default in defaults:
        if len(fixed) >= min_points:
            break
        # Check if similar point already exists
        key_words = default.split()[:3]
        already_there = any(w.lower() in existing_text for w in key_words if len(w) > 4)
        if not already_there:
            fixed.append(default)

    return fixed


def fix_role_name(raw: str) -> str:
    """Fix role name — spelling, acronyms, title case."""
    if not raw or not raw.strip():
        return raw
    text = fix_spelling(raw.strip())
    # Title case each word, keep acronyms uppercase
    acronyms = {'HR', 'AI', 'ML', 'IT', 'UI', 'UX', 'SQL', 'API', 'CRM',
                'ERP', 'LMS', 'SEO', 'SMO', 'POC', 'MBA', 'BBA', 'B.Com'}
    words = text.split()
    result = []
    for w in words:
        if w.upper() in acronyms:
            result.append(w.upper())
        else:
            result.append(w.capitalize())
    return ' '.join(result)
