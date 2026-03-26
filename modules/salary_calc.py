"""
salary_calc.py
Handles all CTC breakup calculations for offer letters.
Analytics Avenue LLP

Standard Indian salary structure:
  Basic        = 40% of CTC (industry standard, tax-efficient floor)
  HRA          = 50% of Basic (metro cities) or 40% (non-metro)
  PF Employer  = 12% of Basic (statutory, can be opted out)
  Variable Pay = % of CTC (annual bonus/incentive component)
  Special All. = Balancer — CTC minus all above components
"""


def calculate_salary_breakup(
    ctc_annual: float,
    base_percent: float = 40.0,
    hra_percent: float = 50.0,
    pf_percent: float = 12.0,
    variable_percent: float = 10.0,
    # Legacy param — kept for backward compat
    pf_opted: bool = None,
) -> dict:
    """
    Calculate full salary breakup from CTC.

    Args:
        ctc_annual       : Total CTC in rupees/year (e.g. 500000 for 5 LPA)
        base_percent     : Basic salary as % of CTC          (default 40%)
        hra_percent      : HRA as % of Basic salary          (default 50%)
        pf_percent       : Employer PF as % of Basic salary  (default 12%, 0 = no PF)
        variable_percent : Variable pay as % of CTC          (default 10%)
    """
    # Handle legacy pf_opted bool (only when pf_percent not explicitly set)
    if pf_opted is not None and pf_percent == 12.0:
        pf_percent = 12.0 if pf_opted else 0.0

    # ── Annual component calculations ────────────────────────────────────────

    # 1. Variable Pay (Annual) — taken off the top of CTC first
    variable_annual = round(ctc_annual * (variable_percent / 100))

    # 2. Fixed CTC pool (everything except variable pay)
    fixed_ctc = ctc_annual - variable_annual

    # 3. Basic = base_percent of CTC (NOT of fixed CTC, industry norm)
    basic_annual = round(ctc_annual * (base_percent / 100))

    # 4. HRA = hra_percent of Basic
    hra_annual = round(basic_annual * (hra_percent / 100))

    # 5. Employer PF = pf_percent of Basic
    pf_annual = round(basic_annual * (pf_percent / 100))

    # 6. Special Allowance = Balancer (ensures total always = CTC)
    #    Special = CTC - Basic - HRA - PF(Employer) - Variable
    known_components = basic_annual + hra_annual + pf_annual + variable_annual
    special_allowance_annual = ctc_annual - known_components

    # Guard: Special Allowance should not go negative
    # (means the chosen percentages are too high — clamp and warn)
    if special_allowance_annual < 0:
        special_allowance_annual = 0
        # Reduce PF first, then HRA to balance
        excess = known_components - ctc_annual
        pf_annual = max(0, pf_annual - excess)
        special_allowance_annual = ctc_annual - (basic_annual + hra_annual + pf_annual + variable_annual)

    # ── Monthly calculations ──────────────────────────────────────────────────
    basic_monthly             = round(basic_annual / 12)
    hra_monthly               = round(hra_annual / 12)
    pf_monthly                = round(pf_annual / 12)
    special_allowance_monthly = round(special_allowance_annual / 12)

    # Gross Monthly = all monthly components (Variable Pay is annual, excluded)
    gross_monthly = basic_monthly + hra_monthly + pf_monthly + special_allowance_monthly

    return {
        # ── Annual figures ────────────────────────────────────────────────────
        "ctc_annual":               ctc_annual,
        "basic_annual":             basic_annual,
        "hra_annual":               hra_annual,
        "pf_annual":                pf_annual,
        "special_allowance_annual": special_allowance_annual,
        "variable_annual":          variable_annual,

        # ── Monthly figures ───────────────────────────────────────────────────
        "basic_monthly":             basic_monthly,
        "hra_monthly":               hra_monthly,
        "pf_monthly":                pf_monthly,
        "special_allowance_monthly": special_allowance_monthly,
        "gross_monthly":             gross_monthly,

        # ── Formatted INR strings ─────────────────────────────────────────────
        "ctc_annual_str":                format_inr(ctc_annual),
        "basic_monthly_str":             format_inr(basic_monthly),
        "hra_monthly_str":               format_inr(hra_monthly),
        "pf_monthly_str":                format_inr(pf_monthly) if pf_percent > 0 else "N/A",
        "special_allowance_monthly_str": format_inr(special_allowance_monthly),
        "variable_annual_str":           format_inr(variable_annual),
        "gross_monthly_str":             format_inr(gross_monthly),

        # ── Meta ──────────────────────────────────────────────────────────────
        "ctc_lpa":    f"{ctc_annual / 100000:.1f} LPA",
        "pf_opted":   pf_percent > 0,
        "pf_percent": pf_percent,
    }


def format_inr(amount: float) -> str:
    """Format a number as Indian Rupees with proper lakh/crore comma style."""
    amount = int(round(amount))
    if amount == 0:
        return "₹0"

    negative = amount < 0
    s = str(abs(amount))

    if len(s) <= 3:
        formatted = s
    else:
        last3 = s[-3:]
        rest = s[:-3]
        parts = []
        while len(rest) > 2:
            parts.append(rest[-2:])
            rest = rest[:-2]
        if rest:
            parts.append(rest)
        parts.reverse()
        formatted = f"{','.join(parts)},{last3}"

    return f"{'−' if negative else ''}₹{formatted}"


def parse_salary_prompt(prompt_text: str) -> dict:
    """Parse a natural language salary prompt (delegates to ai_service)."""
    try:
        from modules.ai_service import parse_salary_prompt_groq
        return parse_salary_prompt_groq(prompt_text)
    except ImportError:
        from modules.ai_service import _fallback_salary_parse
        return _fallback_salary_parse(prompt_text)


# ── Self-test ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    def _show(label, result):
        print(f"\n{'='*55}")
        print(f"  {label}")
        print(f"{'='*55}")
        print(f"  Basic Monthly       : {result['basic_monthly_str']}")
        print(f"  HRA Monthly         : {result['hra_monthly_str']}")
        print(f"  PF Monthly          : {result['pf_monthly_str']}")
        print(f"  Special Allowance   : {result['special_allowance_monthly_str']}")
        print(f"  Gross Monthly       : {result['gross_monthly_str']}")
        print(f"  Variable (Annual)   : {result['variable_annual_str']}")
        print(f"  Total CTC           : {result['ctc_annual_str']}")
        # Verify total
        recon = (result['basic_annual'] + result['hra_annual'] +
                 result['pf_annual'] + result['special_allowance_annual'] +
                 result['variable_annual'])
        match = "✅ MATCH" if recon == result['ctc_annual'] else f"❌ MISMATCH ({recon})"
        print(f"  CTC Reconciliation  : {match}")

    # Test 1: 5 LPA, default structure (40% basic, 50% HRA, 12% PF, 10% variable)
    _show("5 LPA | 40% basic | 50% HRA | 12% PF | 10% variable",
          calculate_salary_breakup(500000))

    # Test 2: 6 LPA, 50% basic, no PF, 5% variable
    _show("6 LPA | 50% basic | 50% HRA | no PF | 5% variable",
          calculate_salary_breakup(600000, base_percent=50, pf_percent=0, variable_percent=5))

    # Test 3: 12 LPA, 40% basic, 12% PF, 20% variable
    _show("12 LPA | 40% basic | 50% HRA | 12% PF | 20% variable",
          calculate_salary_breakup(1200000, base_percent=40, pf_percent=12, variable_percent=20))

    # Test 4: 3.6 LPA (30k/month), no variable, no PF
    _show("3.6 LPA | 40% basic | 50% HRA | no PF | no variable",
          calculate_salary_breakup(360000, pf_percent=0, variable_percent=0))
