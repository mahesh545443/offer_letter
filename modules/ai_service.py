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

BASIC:
- "basic 40%" or "40% base" → basic_annual = CTC × 0.40
- "basic 3.8 LPA" or "3.8 as base" or "base is 3.8" → basic_annual = 380000
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

    # If negative, reduce pf then hra
    if special_annual < 0:
        excess = -special_annual
        pf_reduce = min(pf_m * 12, excess)
        pf_m = int((pf_m * 12 - pf_reduce) / 12)
        excess -= pf_reduce
        if excess > 0:
            hra_reduce = min(hra_m * 12, excess)
            hra_m = int((hra_m * 12 - hra_reduce) / 12)
        special_annual = ctc - (basic_m + hra_m + pf_m) * 12 - variable_a

    special_m = int(special_annual / 12)
    # Fix rounding so gross×12 + variable = CTC exactly
    rounding_diff = ctc - (basic_m + hra_m + pf_m + special_m) * 12 - variable_a
    special_m += int(rounding_diff / 12)
    special_annual = special_m * 12

    # Ensure exact annual reconcile: absorb rounding remainder into special
    actual_total = (basic_m + hra_m + pf_m + special_m) * 12 + variable_a
    if actual_total != ctc:
        diff = ctc - actual_total
        special_m += diff // 12
        # Any sub-monthly remainder: accept ≤11 rs discrepancy in special
        special_annual = special_m * 12
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

    SALARY_KEYWORDS = ['basic', 'base', 'hra', 'pf', 'provident',
                       'variable', 'bonus', 'incentive', 'ctc', 'lpa']

    def _extract_near(keyword, text):
        """Extract number directly adjacent to keyword only."""
        kpos = text.find(keyword)
        if kpos == -1:
            return None
        before = text[:kpos].rstrip()
        after  = text[kpos + len(keyword):]

        # Before: must be IMMEDIATELY before (no other keyword in between)
        # Only look at last 15 chars before keyword
        near_before = before[-15:]
        m = re.search(r'(\d+\.?\d*)\s*%\s*$', near_before)
        if m:
            # Make sure no other salary keyword is between this % and our keyword
            val_end = before.rfind(m.group(1))
            snippet = before[max(0,val_end-5):].strip()
            other_kw = any(kw in snippet and kw != keyword
                          for kw in SALARY_KEYWORDS if kw != 'lpa' and kw != 'ctc')
            if not other_kw:
                return ('pct', float(m.group(1)))
        m = re.search(r'(\d+\.?\d*)\s*lpa?\s*$', near_before)
        if m and float(m.group(1)) < 50:
            return ('lpa', float(m.group(1)))
        m = re.search(r'(\d+\.?\d*)\s+as\s*(?:a\s+|an\s+)?$', near_before)
        if m and float(m.group(1)) < 50:
            return ('lpa', float(m.group(1)))

        # After: look immediately after keyword (skip non-digits up to 10 chars)
        m = re.search(r'^[^\d]{0,10}(\d+\.?\d*)\s*%', after)
        if m:
            return ('pct', float(m.group(1)))
        m = re.search(r'^[^\d]{0,10}(\d+\.?\d*)\s*lpa?', after)
        if m and float(m.group(1)) < 50:
            return ('lpa', float(m.group(1)))
        return None

    # ── BASIC ─────────────────────────────────────────────────
    basic_a = ctc * 0.40  # default
    for kw in ['basic', 'base pay', 'base']:
        res = _extract_near(kw, p)
        if res:
            typ, val = res
            basic_a = ctc * val / 100 if typ == 'pct' else val * 100000
            break

    # ── HRA ───────────────────────────────────────────────────
    hra_a = basic_a * 0.20  # default 20% of basic
    res = _extract_near('hra', p)
    if res:
        typ, val = res
        hra_a = basic_a * val / 100 if typ == 'pct' else val * 100000

    # ── NO-PF check ───────────────────────────────────────────
    no_pf = bool(re.search(
        r'no\s*pf|pf\s*no|without\s*pf|pf\s*opt|\bpf\s*0\b|pf\s*not', p))

    # ── PF ────────────────────────────────────────────────────
    pf_a = basic_a * 0.12  # default
    if no_pf:
        pf_a = 0.0
    else:
        # "X% of Y% of CTC" / "deducting X% on PF towards Y% of CTC"
        m = re.search(
            r'(\d+\.?\d*)\s*%[^%\d]*(\d+\.?\d*)\s*%[^%]*?ctc', p)
        if not m:
            m = re.search(
                r'towards\s*(\d+\.?\d*)\s*%[^%]*?ctc[^%]*(\d+\.?\d*)\s*%', p)
        if m:
            # Two percentages near CTC — one is PF rate, one is CTC base
            v1, v2 = float(m.group(1)), float(m.group(2))
            # Smaller is likely PF rate, larger is CTC base %
            pf_rate = min(v1, v2) / 100
            ctc_base = max(v1, v2) / 100
            pf_a = ctc * ctc_base * pf_rate
        else:
            res = _extract_near('pf', p)
            if not res:
                res = _extract_near('provident', p)
            if res:
                typ, val = res
                pf_a = basic_a * val / 100 if typ == 'pct' else val * 12

    # ── NO-VARIABLE check ─────────────────────────────────────
    no_var = bool(re.search(r'no\s*(?:variable|bonus|incentive)', p))

    # ── VARIABLE ──────────────────────────────────────────────
    var_a = 0.0
    if not no_var:
        for kw in ['variable pay', 'variable', 'bonus', 'incentive']:
            res = _extract_near(kw, p)
            if res:
                typ, val = res
                var_a = ctc * val / 100 if typ == 'pct' else val * 100000
                break

    # ── SPECIAL ALLOWANCE (remainder) ─────────────────────────
    special_a = ctc - basic_a - hra_a - pf_a - var_a
    if special_a < 0:
        # Reduce PF first
        excess = -special_a
        pf_cut = min(pf_a, excess)
        pf_a -= pf_cut; excess -= pf_cut
        if excess > 0:
            hra_a = max(0, hra_a - excess)
        special_a = ctc - basic_a - hra_a - pf_a - var_a

    return _validate_computed_salary({
        "ctc_annual":     int(ctc),
        "basic_monthly":  round(basic_a / 12),
        "hra_monthly":    round(hra_a / 12),
        "pf_monthly":     round(pf_a / 12),
        "variable_annual": round(var_a),
        "pf_opted":       pf_a > 0,
        "ctc_lpa":        f"{ctc/100000:.1f} LPA",
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
