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
    # Try Streamlit secrets first (for cloud deployment)
    try:
        import streamlit as st
        key = st.secrets.get("GROQ_API_KEY", "")
        if key:
            return key
    except Exception:
        pass
    # Fall back to environment variable / .env
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
    """
    client = get_groq_client()

    system_prompt = """You are a salary structure parser for an Indian company HR system.

Extract salary parameters from ANY natural language input.
Return ONLY valid JSON, no explanation, no markdown.

JSON structure (always return all fields):
{
  "ctc_annual": <number in rupees, e.g. 600000 for 6 LPA>,
  "base_percent": <number, % of CTC that is basic salary, default 40>,
  "hra_percent": <number, % of basic that is HRA, default 20>,
  "pf_percent": <number, % of basic for PF, default 5, set 0 if no PF>,
  "variable_percent": <number, % of CTC that is variable/bonus, default 10>
}

Rules:
- CTC: "6 LPA"/"6lpa"/"6 lakhs"/"6L" multiply by 100000
- base/basic: base_percent
- "no pf"/"without pf"/"pf no"/"0 pf"/"pf opted out" → pf_percent: 0
- "pf yes"/"with pf" (no % given) → pf_percent: 5
- "1% pf"/"12% pf" → use that exact number
- variable/bonus/incentive → variable_percent
- Always return valid numbers, never null"""

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
    """Ensure all salary params are valid numbers."""
    ctc  = float(params.get("ctc_annual", 600000) or 600000)
    base = float(params.get("base_percent", 40) or 40)
    hra  = float(params.get("hra_percent", 20) or 20)
    var  = float(params.get("variable_percent", 10) or 10)

    if "pf_percent" in params:
        pf_pct = float(params.get("pf_percent") or 0)
    elif "pf_opted" in params:
        pf_pct = 5.0 if params.get("pf_opted") else 0.0
    else:
        pf_pct = 5.0

    if ctc < 100000: ctc *= 100000
    if base > 100: base = 100
    if base < 1:  base = 40
    if hra > 100: hra = 20
    if var > 100: var = 10
    if var < 0:   var = 0
    if pf_pct < 0: pf_pct = 0
    if pf_pct > 30: pf_pct = 12

    return {
        "ctc_annual":       ctc,
        "base_percent":     base,
        "hra_percent":      hra,
        "pf_percent":       pf_pct,
        "pf_opted":         pf_pct > 0,
        "variable_percent": var,
    }


def _fallback_salary_parse(prompt_text: str) -> dict:
    """Fallback used ONLY when Groq is completely unavailable."""
    p = prompt_text.lower().strip()
    p = re.sub(r'\bper[a-z]{0,6}[nc][te]{0,2}\b', 'percent', p)
    p = re.sub(r'[.,;/]+', ' ', p)
    p = re.sub(r'\s+', ' ', p).strip()

    ctc_annual = 600000.0
    m = re.search(r'(\d+\.?\d*)\s*(?:lpa|lakh|lakhs|l\b)', p)
    if m:
        ctc_annual = float(m.group(1)) * 100000

    no_pf = bool(re.search(
        r'no\s*pf|pf\s*no|without\s*pf|pf\s*opt(?:ed)?\s*out|\b0\s*(?:percent|%)?\s*pf\b|pf\s*0\b', p
    ))

    def _get(before_kw, after_kw, default):
        m = re.search(rf'(?:{before_kw})\s*(?:is|:)?\s*(\d+\.?\d*)\s*(?:percent|%)?', p)
        if m: return float(m.group(1))
        m = re.search(rf'(\d+\.?\d*)\s*(?:percent|%)\s*(?:{after_kw})', p)
        if m: return float(m.group(1))
        return default

    base_percent     = _get(r'bas(?:e|ic)(?:\s+pay)?', r'bas(?:e|ic)', 40.0)
    hra_percent      = _get(r'hra|house\s*rent(?:\s*allowance)?', r'hra|house\s*rent', 20.0)
    variable_percent = _get(r'variable(?:\s+pay)?|bonus|incentive', r'variable|bonus|incentive', 10.0)
    pf_percent       = 0.0 if no_pf else _get(
        r'(?:employer\s+)?(?:pf|provident\s*fund|epf)', r'pf|provident\s*fund|epf', 5.0)

    return _validate_salary_params({
        "ctc_annual": ctc_annual, "base_percent": base_percent,
        "hra_percent": hra_percent, "pf_percent": pf_percent,
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

    name_match = re.search(r'for\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)', prompt_text)
    candidate_name = name_match.group(1) if name_match else None
    ctc_match = re.search(r'(\d+\.?\d*)\s*lpa', p)
    ctc_lpa = float(ctc_match.group(1)) if ctc_match else None
    dur_match = re.search(r'(\d+)\s*month', p)
    duration_months = int(dur_match.group(1)) if dur_match else None
    role_match = re.search(r'[–\-]\s*([A-Za-z\s]+?)(?:\s*[–\-]|$)', prompt_text)
    role = role_match.group(1).strip() if role_match else None

    return {
        "document_type": doc_type, "candidate_name": candidate_name,
        "role": role, "ctc_lpa": ctc_lpa,
        "duration_months": duration_months, "joining_date": None, "salary_notes": None,
    }
