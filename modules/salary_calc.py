"""
salary_calc.py
Handles all CTC breakup calculations for offer letters.
PF is now a configurable % of basic (default 5%, 0 = no PF).
Analytics Avenue LLP
"""


def calculate_salary_breakup(ctc_annual: float, base_percent: float = 40,
                               hra_percent: float = 20, pf_percent: float = 5.0,
                               variable_percent: float = 10,
                               # Legacy param — kept for backward compat
                               pf_opted: bool = None) -> dict:
    """
    Calculate full salary breakup from CTC.

    Args:
        ctc_annual      : Total CTC in rupees/year (e.g. 600000 for 6 LPA)
        base_percent    : Basic salary as % of CTC (default 40%)
        hra_percent     : HRA as % of basic (default 20%)
        pf_percent      : PF as % of basic (default 5%, set 0 for no PF)
        variable_percent: Variable pay as % of CTC (default 10%)
        pf_opted        : Legacy bool — if provided and pf_percent not set,
                          True=5%, False=0%
    """
    # Handle legacy pf_opted bool
    if pf_opted is not None and pf_percent == 5.0:
        pf_percent = 5.0 if pf_opted else 0.0

    # ── Annual calculations ───────────────────────────────────
    basic_annual    = round(ctc_annual * base_percent / 100)
    hra_annual      = round(basic_annual * hra_percent / 100)
    pf_annual       = round(basic_annual * pf_percent / 100)
    variable_annual = round(ctc_annual * variable_percent / 100)

    # Special allowance = whatever remains after all components
    fixed_components        = basic_annual + hra_annual + pf_annual + variable_annual
    special_allowance_annual = ctc_annual - fixed_components

    # ── Monthly calculations ──────────────────────────────────
    basic_monthly            = round(basic_annual / 12)
    hra_monthly              = round(hra_annual / 12)
    pf_monthly               = round(pf_annual / 12)
    special_allowance_monthly = round(special_allowance_annual / 12)
    gross_monthly            = basic_monthly + hra_monthly + pf_monthly + special_allowance_monthly

    return {
        # Annual
        "ctc_annual":               ctc_annual,
        "basic_annual":             basic_annual,
        "hra_annual":               hra_annual,
        "pf_annual":                pf_annual,
        "special_allowance_annual": special_allowance_annual,
        "variable_annual":          variable_annual,

        # Monthly
        "basic_monthly":             basic_monthly,
        "hra_monthly":               hra_monthly,
        "pf_monthly":                pf_monthly,
        "special_allowance_monthly": special_allowance_monthly,
        "gross_monthly":             gross_monthly,

        # Formatted strings
        "ctc_annual_str":                format_inr(ctc_annual),
        "basic_monthly_str":             format_inr(basic_monthly),
        "hra_monthly_str":               format_inr(hra_monthly),
        "pf_monthly_str":                format_inr(pf_monthly) if pf_percent > 0 else "N/A",
        "special_allowance_monthly_str": format_inr(special_allowance_monthly),
        "variable_annual_str":           format_inr(variable_annual),
        "gross_monthly_str":             format_inr(gross_monthly),

        # LPA string
        "ctc_lpa":  f"{ctc_annual / 100000:.1f} LPA",
        "pf_opted": pf_percent > 0,
        "pf_percent": pf_percent,
    }


def format_inr(amount: float) -> str:
    """Format number as Indian Rupee string with commas."""
    amount = int(amount)
    if amount == 0:
        return "₹0"
    s = str(abs(amount))
    if len(s) <= 3:
        return f"₹{s}"
    last3 = s[-3:]
    rest = s[:-3]
    parts = []
    while len(rest) > 2:
        parts.append(rest[-2:])
        rest = rest[:-2]
    if rest:
        parts.append(rest)
    parts.reverse()
    return f"₹{','.join(parts)},{last3}"


def parse_salary_prompt(prompt_text: str) -> dict:
    """
    Fallback rule-based salary parser (used if Groq unavailable).
    """
    import re
    from modules.ai_service import _fallback_salary_parse
    return _fallback_salary_parse(prompt_text)


if __name__ == "__main__":
    # Test: 6 LPA, 50% base, 1% PF, 5% variable
    print("=== Test: 6 LPA, 50% base, 1% PF, 5% variable ===")
    r = calculate_salary_breakup(600000, base_percent=50, pf_percent=1, variable_percent=5)
    print(f"Basic Monthly:      {r['basic_monthly_str']}")
    print(f"HRA Monthly:        {r['hra_monthly_str']}")
    print(f"PF Monthly:         {r['pf_monthly_str']}")
    print(f"Special Allowance:  {r['special_allowance_monthly_str']}")
    print(f"Gross Monthly:      {r['gross_monthly_str']}")
    print(f"Variable Annual:    {r['variable_annual_str']}")
    print(f"Total CTC:          {r['ctc_annual_str']}")
    print()

    # Test: no PF
    print("=== Test: 6 LPA, 40% base, no PF, 10% variable ===")
    r2 = calculate_salary_breakup(600000, base_percent=40, pf_percent=0, variable_percent=10)
    print(f"Basic Monthly:      {r2['basic_monthly_str']}")
    print(f"PF Monthly:         {r2['pf_monthly_str']}")
    print(f"Special Allowance:  {r2['special_allowance_monthly_str']}")
    print(f"Gross Monthly:      {r2['gross_monthly_str']}")
