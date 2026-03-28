"""
ai_service.py
Analytics Avenue LLP
Approach: Groq performs ALL salary math and returns final computed rupee amounts.
HR can type ANY formula — Groq calculates, we just display.
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
    """Parse HR letter generation prompt."""
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
    HR types ANY salary description in plain English.
    Groq performs ALL the math and returns final computed rupee amounts.
    We never trust just percentages — Groq calculates the actual numbers.
    """
    client = get_groq_client()

    system_prompt = """You are a salary calculator for an Indian company HR system.
HR will describe a salary structure in plain English. You must CALCULATE and return the final rupee amounts.

STEP 1 — Extract CTC:
- "5 LPA" / "5 lakhs" / "5L" = 500000 rupees annual
- "monthly 40000" / "40k/month" = 480000 annual
- Always work in annual rupees internally

STEP 2 — Calculate each component using whatever formula HR describes:
Examples of what HR might say:
  "basic 40%" → basic_annual = CTC × 40%
  "basic 50% of CTC" → basic_annual = CTC × 50%
  "PF 12% of basic" → pf_annual = basic_annual × 12%
  "PF 12% of 70% of CTC" → pf_annual = (CTC × 70%) × 12%
  "PF 12% on 60% CTC" → pf_annual = (CTC × 60%) × 12%
  "PF 780 per month" → pf_annual = 780 × 12 = 9360
  "PF on statutory ceiling 15000" → pf_annual = 15000 × 12% × 12
  "HRA 50% of basic" → hra_annual = basic_annual × 50%
  "HRA 20% of CTC" → hra_annual = CTC × 20%
  "variable 10%" → variable_annual = CTC × 10%
  "bonus 1 lakh" → variable_annual = 100000
  "no PF" / "PF opted out" → pf_annual = 0
  "no variable" / "no bonus" → variable_annual = 0

STEP 3 — Calculate special_allowance_annual:
  special_allowance_annual = CTC - basic_annual - hra_annual - pf_annual - variable_annual
  (This must never be negative. If it goes negative, reduce pf first, then hra.)

STEP 4 — Return all monthly values (annual ÷ 12, rounded to nearest integer):

Return ONLY this JSON, no explanation, no markdown:
{
  "ctc_annual": <integer>,
  "basic_monthly": <integer>,
  "hra_monthly": <integer>,
  "pf_monthly": <integer>,
  "special_allowance_monthly": <integer>,
  "gross_monthly": <integer>,
  "variable_annual": <integer>,
  "pf_opted": <true or false>,
  "ctc_lpa": "<e.g. 5.0 LPA>"
}

gross_monthly = basic_monthly + hra_monthly + pf_monthly + special_allowance_monthly
pf_opted = true if pf_monthly > 0 else false

VERIFY: (gross_monthly × 12) + variable_annual must equal ctc_annual (allow ±12 rounding)"""

    if client:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": prompt_text}
                ],
                temperature=0.1, max_tokens=300,
            )
            raw = response.choices[0].message.content.strip()
            raw = re.sub(r"```json|```", "", raw).strip()
            result = json.loads(raw)

            # ── Rule-based overrides for binary flags ──────────
            p_lower = prompt_text.lower()
            NO_PF = ["no pf","pf no","without pf","pf opted out","opt out pf",
                     "pf opt out","pf 0","0% pf","no provident","without provident",
                     "pf not applicable","pf waived","no epf","without epf"]
            NO_VAR = ["no variable","no bonus","no incentive","without variable",
                      "without bonus","0% variable","variable 0","fixed only",
                      "no performance pay"]
            if any(pat in p_lower for pat in NO_PF):
                result["pf_monthly"] = 0
                result["pf_opted"]   = False
            if any(pat in p_lower for pat in NO_VAR):
                result["variable_annual"] = 0

            return _validate_computed_salary(result, prompt_text)

        except Exception as e:
            print(f"Groq salary parse error: {e}")

    return _fallback_salary_parse(prompt_text)


def _validate_computed_salary(r: dict, prompt_text: str = "") -> dict:
    """
    Validate Groq-computed salary amounts.
    Recomputes special allowance to ensure CTC always reconciles.
    """
    ctc          = int(float(r.get("ctc_annual", 600000) or 600000))
    basic_m      = int(float(r.get("basic_monthly", 0) or 0))
    hra_m        = int(float(r.get("hra_monthly", 0) or 0))
    pf_m         = int(float(r.get("pf_monthly", 0) or 0))
    variable_a   = int(float(r.get("variable_annual", 0) or 0))
    pf_opted     = bool(r.get("pf_opted", pf_m > 0))

    # CTC sanity — if LLM returned LPA instead of rupees
    if ctc < 1000:   ctc *= 100000
    elif ctc < 1000: ctc *= 10000

    # Basic sanity — must be 20-70% of CTC monthly
    ctc_monthly = ctc / 12
    if basic_m < ctc_monthly * 0.15 or basic_m > ctc_monthly * 0.80:
        basic_m = int(ctc_monthly * 0.40)  # fallback to 40%

    # HRA sanity — must be > 0 and < basic
    if hra_m <= 0 or hra_m > basic_m:
        hra_m = int(basic_m * 0.50)  # fallback to 50% of basic

    # PF sanity
    if pf_m < 0:
        pf_m = 0
    if not pf_opted:
        pf_m = 0

    # Variable sanity
    if variable_a < 0:
        variable_a = 0
    if variable_a > ctc * 0.50:
        variable_a = int(ctc * 0.10)

    # ── Recompute special allowance to ensure CTC reconciles ──
    known_annual    = (basic_m + hra_m + pf_m) * 12 + variable_a
    special_annual  = ctc - known_annual
    if special_annual < 0:
        # Reduce PF first
        excess   = -special_annual
        pf_cut   = min(pf_m * 12, excess)
        pf_m     = int((pf_m * 12 - pf_cut) / 12)
        excess   -= pf_cut
        # Then reduce HRA
        if excess > 0:
            hra_cut = min(hra_m * 12, excess)
            hra_m   = int((hra_m * 12 - hra_cut) / 12)
        special_annual = ctc - (basic_m + hra_m + pf_m) * 12 - variable_a

    special_m = int(special_annual / 12)
    gross_m   = basic_m + hra_m + pf_m + special_m

    from modules.salary_calc import format_inr
    return {
        # ── Raw amounts ──────────────────────────────────────
        "ctc_annual":               ctc,
        "basic_annual":             basic_m * 12,
        "hra_annual":               hra_m * 12,
        "pf_annual":                pf_m * 12,
        "special_allowance_annual": special_annual,
        "variable_annual":          variable_a,
        "basic_monthly":            basic_m,
        "hra_monthly":              hra_m,
        "pf_monthly":               pf_m,
        "special_allowance_monthly":special_m,
        "gross_monthly":            gross_m,
        # ── Formatted strings ────────────────────────────────
        "ctc_annual_str":                format_inr(ctc),
        "basic_monthly_str":             format_inr(basic_m),
        "hra_monthly_str":               format_inr(hra_m),
        "pf_monthly_str":                format_inr(pf_m) if pf_m > 0 else "N/A",
        "special_allowance_monthly_str": format_inr(special_m),
        "variable_annual_str":           format_inr(variable_a),
        "gross_monthly_str":             format_inr(gross_m),
        # ── Meta ─────────────────────────────────────────────
        "ctc_lpa":    r.get("ctc_lpa", f"{ctc/100000:.1f} LPA"),
        "pf_opted":   pf_m > 0,
        "pf_percent": round((pf_m * 12 / (basic_m * 12) * 100), 1) if basic_m > 0 and pf_m > 0 else 0,
        # ── Legacy keys for salary_calc compatibility ────────
        "base_percent":     round(basic_m * 12 / ctc * 100, 1),
        "hra_percent":      round(hra_m / basic_m * 100, 1) if basic_m > 0 else 50.0,
        "variable_percent": round(variable_a / ctc * 100, 1),
    }


def _fallback_salary_parse(prompt_text: str) -> dict:
    """Rule-based fallback when Groq is completely unavailable."""
    import re
    p = prompt_text.lower().strip()
    p = re.sub(r'[.,;/]+', ' ', p)
    p = re.sub(r'\s+', ' ', p).strip()

    # CTC
    ctc = 600000.0
    m = re.search(r'(\d+\.?\d*)\s*(?:lpa|lakh(?:s)?|l\b)', p)
    if m:
        ctc = float(m.group(1)) * 100000
    else:
        m = re.search(r'(\d+\.?\d*)\s*k?\s*(?:monthly|per\s*month|pm\b)', p)
        if m:
            val = float(m.group(1))
            ctc = (val * 1000 if val < 1000 else val) * 12

    # Basic
    base_pct = 40.0
    m = re.search(r'bas(?:e|ic)[^\d]*(\d+\.?\d*)\s*%', p)
    if m: base_pct = float(m.group(1))

    # HRA
    hra_pct = 50.0
    m = re.search(r'hra[^\d]*(\d+\.?\d*)\s*%', p)
    if m: hra_pct = float(m.group(1))

    # PF
    no_pf = bool(re.search(r'no\s*pf|pf\s*no|without\s*pf|pf\s*opt|pf\s*0', p))
    pf_pct = 0.0
    if not no_pf:
        # "PF 12% of 70% CTC"
        m = re.search(r'pf\s*(\d+\.?\d*)\s*%\s*(?:of\s*)?(\d+\.?\d*)\s*%\s*(?:of\s*)?ctc', p)
        if m:
            pf_base = ctc * float(m.group(2)) / 100
            pf_pct_val = float(m.group(1))
            pf_annual = pf_base * pf_pct_val / 100
        else:
            m = re.search(r'pf\s*(\d+\.?\d*)\s*%', p)
            pf_pct = float(m.group(1)) if m else 12.0
            pf_annual = None
    else:
        pf_annual = 0.0

    # Variable
    no_var = bool(re.search(r'no\s*(?:variable|bonus|incentive)', p))
    var_pct = 0.0 if no_var else 10.0
    m = re.search(r'(?:variable|bonus|incentive)[^\d]*(\d+\.?\d*)\s*%', p)
    if m and not no_var: var_pct = float(m.group(1))

    # Compute
    basic_a    = ctc * base_pct / 100
    hra_a      = basic_a * hra_pct / 100
    if pf_annual is None:
        pf_a = basic_a * pf_pct / 100
    else:
        pf_a = pf_annual
    var_a      = ctc * var_pct / 100
    special_a  = ctc - basic_a - hra_a - pf_a - var_a
    if special_a < 0: special_a = 0

    return _validate_computed_salary({
        "ctc_annual":    ctc,
        "basic_monthly": int(basic_a / 12),
        "hra_monthly":   int(hra_a / 12),
        "pf_monthly":    int(pf_a / 12),
        "variable_annual": int(var_a),
        "pf_opted":      pf_a > 0,
        "ctc_lpa":       f"{ctc/100000:.1f} LPA",
    }, prompt_text)


def _fallback_parse(prompt_text: str) -> dict:
    p = prompt_text.lower()
    if any(x in p for x in ["pre-offer","pre offer","preoffer"]):
        doc_type = "pre_offer"
    elif any(x in p for x in ["offer letter","offer"]):
        doc_type = "offer_letter"
    elif any(x in p for x in ["internship","intern"]):
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
