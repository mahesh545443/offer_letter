"""
salary_calc.py
Analytics Avenue LLP
Now acts as display/format layer only.
All calculations are done by Groq in ai_service.py.
salary_calc is kept for legacy compatibility and direct calls.
"""


def calculate_salary_breakup(
    ctc_annual: float,
    base_percent: float = 40.0,
    hra_percent: float = 50.0,
    pf_percent: float = 12.0,
    variable_percent: float = 10.0,
    pf_opted: bool = None,
) -> dict:
    """
    Direct calculation (used when params are already known percentages).
    Groq now returns pre-computed amounts via parse_salary_prompt_groq,
    but this function is kept for any direct/legacy calls.
    """
    if pf_opted is not None and pf_percent == 12.0:
        pf_percent = 12.0 if pf_opted else 0.0

    variable_annual          = round(ctc_annual * (variable_percent / 100))
    basic_annual             = round(ctc_annual * (base_percent / 100))
    hra_annual               = round(basic_annual * (hra_percent / 100))
    pf_annual                = round(basic_annual * (pf_percent / 100))
    known                    = basic_annual + hra_annual + pf_annual + variable_annual
    special_allowance_annual = ctc_annual - known

    if special_allowance_annual < 0:
        excess = -special_allowance_annual
        pf_cut = min(pf_annual, excess)
        pf_annual -= pf_cut
        excess    -= pf_cut
        if excess > 0:
            hra_annual = max(0, hra_annual - excess)
        special_allowance_annual = ctc_annual - (basic_annual + hra_annual + pf_annual + variable_annual)

    basic_monthly             = round(basic_annual / 12)
    hra_monthly               = round(hra_annual / 12)
    pf_monthly                = round(pf_annual / 12)
    special_allowance_monthly = round(special_allowance_annual / 12)
    gross_monthly             = basic_monthly + hra_monthly + pf_monthly + special_allowance_monthly

    return {
        "ctc_annual":               ctc_annual,
        "basic_annual":             basic_annual,
        "hra_annual":               hra_annual,
        "pf_annual":                pf_annual,
        "special_allowance_annual": special_allowance_annual,
        "variable_annual":          variable_annual,
        "basic_monthly":            basic_monthly,
        "hra_monthly":              hra_monthly,
        "pf_monthly":               pf_monthly,
        "special_allowance_monthly":special_allowance_monthly,
        "gross_monthly":            gross_monthly,
        "ctc_annual_str":                format_inr(ctc_annual),
        "basic_monthly_str":             format_inr(basic_monthly),
        "hra_monthly_str":               format_inr(hra_monthly),
        "pf_monthly_str":                format_inr(pf_monthly) if pf_percent > 0 else "N/A",
        "special_allowance_monthly_str": format_inr(special_allowance_monthly),
        "variable_annual_str":           format_inr(variable_annual),
        "gross_monthly_str":             format_inr(gross_monthly),
        "ctc_lpa":    f"{ctc_annual / 100000:.1f} LPA",
        "pf_opted":   pf_percent > 0,
        "pf_percent": pf_percent,
    }


def format_inr(amount: float) -> str:
    """Format as Indian Rupees with lakh/crore comma style."""
    amount = int(round(amount))
    if amount == 0:
        return "\u20b90"
    negative = amount < 0
    s = str(abs(amount))
    if len(s) <= 3:
        formatted = s
    else:
        last3 = s[-3:]
        rest  = s[:-3]
        parts = []
        while len(rest) > 2:
            parts.append(rest[-2:])
            rest = rest[:-2]
        if rest:
            parts.append(rest)
        parts.reverse()
        formatted = f"{','.join(parts)},{last3}"
    return f"{'−' if negative else ''}\u20b9{formatted}"


def parse_salary_prompt(prompt_text: str) -> dict:
    """Delegates to ai_service Groq parser."""
    try:
        from modules.ai_service import parse_salary_prompt_groq
        return parse_salary_prompt_groq(prompt_text)
    except Exception:
        from modules.ai_service import _fallback_salary_parse
        return _fallback_salary_parse(prompt_text)


if __name__ == "__main__":
    def _show(label, r):
        print(f"\n{'='*55}\n  {label}\n{'='*55}")
        print(f"  Basic      : {r['basic_monthly_str']}")
        print(f"  HRA        : {r['hra_monthly_str']}")
        print(f"  PF         : {r['pf_monthly_str']}")
        print(f"  Special    : {r['special_allowance_monthly_str']}")
        print(f"  Gross/mo   : {r['gross_monthly_str']}")
        print(f"  Variable/y : {r['variable_annual_str']}")
        print(f"  Total CTC  : {r['ctc_annual_str']}")
        recon = (r['basic_annual'] + r['hra_annual'] + r['pf_annual'] +
                 r['special_allowance_annual'] + r['variable_annual'])
        print(f"  Reconcile  : {'MATCH' if recon == r['ctc_annual'] else f'MISMATCH ({recon})'}")

    _show("5 LPA | 40% basic | 50% HRA | 12% PF | 10% variable",
          calculate_salary_breakup(500000))
    _show("6 LPA | 50% basic | no PF | 5% variable",
          calculate_salary_breakup(600000, base_percent=50, pf_percent=0, variable_percent=5))
    _show("10 LPA | 45% basic | 12% PF | 20% variable",
          calculate_salary_breakup(1000000, base_percent=45, pf_percent=12, variable_percent=20))
