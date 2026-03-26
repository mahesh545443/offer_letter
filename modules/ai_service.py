"""
ai_service.py
Uses Groq API to parse natural language prompts into structured data.
Supports both .env (local) and Streamlit Secrets (cloud deployment).
Analytics Avenue LLP
"""

import os
import json
import re
from dotenv import load_dotenv

load_dotenv()


def _get_groq_key() -> str:
    """Get Groq API key from Streamlit secrets (cloud) or .env (local)."""
    try:
        import streamlit as st
        key = st.secrets.get("GROQ_API_KEY", "")
        if key:
            return key
    except Exception:
        pass
    return os.getenv("GROQ_API_KEY", "")


def get_groq_client(model=None):
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
                    {"role": "user", "content": prompt_text}
                ],
                temperature=0.1,
                max_tokens=300,
            )
            raw = response.choices[0].message.content.strip()
            raw = re.sub(r"```json|```", "", raw).strip()
            return json.loads(raw)
        except Exception as e:
            print(f"Groq parse error: {e}")

    return _fallback_parse(prompt_text)


def parse_salary_prompt_groq(prompt_text: str, model: str = "llama3-8b-8192") -> dict:
    """
    Parse ANY natural language salary prompt using Groq.
    Falls back to rule-based parser if Groq unavailable.

    KEY FIX: Groq is explicitly told to return ONLY percentages (never absolute
    rupee amounts) for base/hra/pf/variable. The old prompt was ambiguous and
    caused Groq to sometimes return e.g. base_percent=5000 (an absolute value).
    """
    client = get_groq_client()

    system_prompt = """You are a salary structure parser for an Indian company HR system.
Extract salary PARAMETERS from natural language. Return ONLY valid JSON, no explanation, no markdown.

CRITICAL RULES:
1. ctc_annual = total CTC in FULL RUPEES. Examples: 5 LPA → 500000, 6 LPA → 600000, 12 LPA → 1200000
2. base_percent = Basic salary as PERCENTAGE of CTC. Must be 30-60. Default: 40
3. hra_percent = HRA as PERCENTAGE of BASIC salary. Must be 10-50. Default: 50
4. pf_percent = Employer PF as PERCENTAGE of BASIC salary. Default: 12. Set 0 if "no pf" / "pf opted out".
5. variable_percent = Variable/bonus as PERCENTAGE of CTC. Default: 10. Set 0 if "no variable"/"no bonus".

NEVER return absolute rupee values for percentages. ONLY percentages.

Conversion examples:
- "5 lpa" / "5 lakhs" / "5L" → ctc_annual: 500000
- "monthly 40000" / "40k monthly" → ctc_annual: 480000
- "basic 50%" → base_percent: 50
- "hra 40% of basic" → hra_percent: 40
- "no pf" / "pf opted out" → pf_percent: 0
- "pf 12%" → pf_percent: 12
- "10% variable" → variable_percent: 10
- "no variable" / "no bonus" → variable_percent: 0
- "1 lakh bonus" on 6 LPA → variable_percent: 16 (100000/600000*100)

Return JSON:
{
  "ctc_annual": <integer, full rupees>,
  "base_percent": <number 30-60>,
  "hra_percent": <number 10-50>,
  "pf_percent": <number 0-12>,
  "variable_percent": <number 0-30>
}"""

    if client:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt_text}
                ],
                temperature=0.1,
                max_tokens=200,
            )
            raw = response.choices[0].message.content.strip()
            raw = re.sub(r"```json|```", "", raw).strip()
            result = json.loads(raw)
            return _validate_salary_params(result)
        except Exception as e:
            print(f"Groq salary parse error: {e}")

    return _fallback_salary_parse(prompt_text)


def _validate_salary_params(params: dict) -> dict:
    """
    Validate and sanitize all salary params.

    KEY FIX: The old validator had `if ctc < 100000: ctc *= 100000` which
    was the ONLY guard — if Groq returned base_percent=5000 (absolute rupees)
    it would pass right through. Now we clamp every percentage field tightly.
    """
    # ── CTC ──────────────────────────────────────────────────────────────────
    ctc = float(params.get("ctc_annual", 600000) or 600000)
    if   ctc < 1000:   ctc *= 100000   # e.g. LLM returned 5   (LPA)  → 500000
    elif ctc < 10000:  ctc *= 10000    # e.g. LLM returned 50  (×10k) → 500000
    elif ctc < 100000: ctc *= 1000     # e.g. LLM returned 500 (×1k)  → 500000

    # ── Percentages ──────────────────────────────────────────────────────────
    # If any value is > 100 the LLM returned an absolute amount — use default instead.
    def _safe_pct(key, default, lo, hi):
        val = float(params.get(key, default) or default)
        if val < lo or val > hi:
            return float(default)
        return val

    base_percent     = _safe_pct("base_percent",     40.0,  30,  60)
    hra_percent      = _safe_pct("hra_percent",       50.0,  10,  50)
    variable_percent = _safe_pct("variable_percent",  10.0,   0,  30)
    pf_percent       = _safe_pct("pf_percent",        12.0,   0,  30)

    # Guard: Basic% + Variable% must not exceed 95% of CTC
    if base_percent + variable_percent > 95:
        variable_percent = max(0.0, 95.0 - base_percent)

    return {
        "ctc_annual":       ctc,
        "base_percent":     base_percent,
        "hra_percent":      hra_percent,
        "pf_percent":       pf_percent,
        "pf_opted":         pf_percent > 0,
        "variable_percent": variable_percent,
    }


def _fallback_salary_parse(prompt_text: str) -> dict:
    """Rule-based fallback used ONLY when Groq is completely unavailable."""
    p = prompt_text.lower().strip()
    p = re.sub(r'\bper[a-z]{0,6}[nc][te]{0,2}\b', 'percent', p)
    p = re.sub(r'[.,;/]+', ' ', p)
    p = re.sub(r'\s+', ' ', p).strip()

    # ── CTC ──────────────────────────────────────────────────────────────────
    ctc_annual = 600000.0
    m = re.search(r'(\d+\.?\d*)\s*(?:lpa|lakh(?:s)?|l\b)', p)
    if m:
        ctc_annual = float(m.group(1)) * 100000
    else:
        # "monthly gross 40000" or "40k monthly"
        m = re.search(
            r'(?:monthly\s+(?:gross|salary|ctc)?\s*(?:of|is|:)?\s*)?'
            r'(\d+\.?\d*)\s*k?\s*(?:monthly|per\s*month|pm\b)', p
        )
        if m:
            val = float(m.group(1))
            if val < 1000:
                val *= 1000  # "40k" → 40000
            ctc_annual = val * 12

    # ── PF detection ─────────────────────────────────────────────────────────
    no_pf = bool(re.search(
        r'no\s*pf|pf\s*no|without\s*pf|pf\s*opt(?:ed)?\s*out'
        r'|\b0\s*(?:percent|%)?\s*pf\b|pf\s*0\b', p
    ))

    def _get_pct(before_kw, after_kw, default):
        m = re.search(
            rf'(?:{before_kw})\s*(?:of\s+(?:basic|ctc))?\s*(?:is|=|:)?\s*'
            rf'(\d+\.?\d*)\s*(?:percent|%)?', p
        )
        if m:
            return float(m.group(1))
        m = re.search(
            rf'(\d+\.?\d*)\s*(?:percent|%)\s*(?:of\s+(?:basic|ctc)\s+)?(?:{after_kw})', p
        )
        if m:
            return float(m.group(1))
        return default

    base_percent     = _get_pct(r'bas(?:e|ic)(?:\s+(?:pay|salary))?', r'bas(?:e|ic)', 40.0)
    hra_percent      = _get_pct(r'hra|house\s*rent(?:\s*allowance)?',  r'hra',          50.0)
    variable_percent = _get_pct(r'variable(?:\s+pay)?|bonus|incentive', r'variable|bonus|incentive', 10.0)
    pf_percent       = 0.0 if no_pf else _get_pct(
        r'(?:employer\s+)?(?:pf|provident\s*fund|epf)',
        r'pf|provident\s*fund|epf', 12.0
    )

    return _validate_salary_params({
        "ctc_annual":       ctc_annual,
        "base_percent":     base_percent,
        "hra_percent":      hra_percent,
        "pf_percent":       pf_percent,
        "variable_percent": variable_percent,
    })


def _fallback_parse(prompt_text: str) -> dict:
    """Rule-based fallback for document type parsing."""
    p = prompt_text.lower()
    if any(x in p for x in ["pre-offer", "pre offer", "preoffer"]):
        doc_type = "pre_offer"
    elif any(x in p for x in ["offer letter", "offer"]):
        doc_type = "offer_letter"
    elif any(x in p for x in ["internship", "intern"]):
        doc_type = "internship"
    else:
        doc_type = "pre_offer"

    name_match     = re.search(r'for\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)', prompt_text)
    candidate_name = name_match.group(1) if name_match else None
    ctc_match      = re.search(r'(\d+\.?\d*)\s*lpa', p)
    ctc_lpa        = float(ctc_match.group(1)) if ctc_match else None
    dur_match      = re.search(r'(\d+)\s*month', p)
    duration_months = int(dur_match.group(1)) if dur_match else None
    role_match     = re.search(r'[–\-]\s*([A-Za-z\s]+?)(?:\s*[–\-]|$)', prompt_text)
    role           = role_match.group(1).strip() if role_match else None

    return {
        "document_type":  doc_type,
        "candidate_name": candidate_name,
        "role":           role,
        "ctc_lpa":        ctc_lpa,
        "duration_months": duration_months,
        "joining_date":   None,
        "salary_notes":   None,
    }
