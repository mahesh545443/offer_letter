# Analytics Avenue LLP — HR Letter Generator

Automated HR document generation system using Streamlit + docxtpl + Groq AI.

---

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Your Groq API Key

Open `.env` and replace with your actual key:
```
GROQ_API_KEY=your_actual_groq_api_key_here
```
Get your free key at: https://console.groq.com

### 3. Create Word Templates (MANUAL STEP — Required)

You must create 3 Word (.docx) files in the `templates/` folder.
See template instructions below.

### 4. Run the App

```bash
streamlit run app.py
```

---

## ⚠️ MANUAL STEPS REQUIRED

### Step 1: Create Templates in Microsoft Word

You need to create these 3 files in the `templates/` folder:

---

#### File 1: `templates/pre_offer_template.docx`

Design your pre-offer letter exactly as it looks now (letterhead, logo, all points).
Replace only the changing parts with these placeholders:

```
{{ salutation }}         → Ms. or Mr.
{{ candidate_name }}     → Full name of candidate
{{ role }}               → Job role/position
{{ joining_date }}       → Date of joining (e.g. 03-04-2026)
{{ letter_date }}        → Date on the letter
```

Example usage in Word:
```
This is to formally acknowledge that {{ salutation }} {{ candidate_name }} has been
engaged with Analytics Avenue LLP in the role of {{ role }}
The actual engagement shall commence with a probationary period ranging from two to
four months, effective from {{ joining_date }}, the date of joining.
```

Everything else (compensation details, Points to Be Noted 1-5, notice period,
signature block, acceptance block) stays exactly as is in the Word file.

---

#### File 2: `templates/internship_template.docx`

Design your internship completion certificate. Use these placeholders:

```
{{ salutation }}         → Ms. or Mr.
{{ intern_name }}        → Full name
{{ reg_no }}             → Registration number
{{ college }}            → College/Institution
{{ department }}         → Department
{{ role }}               → Internship role
{{ start_date }}         → Start date
{{ end_date }}           → End date
{{ duration }}           → e.g. "one month"
{{ letter_date }}        → Date on the letter
```

For the responsibilities bullet list, use this Jinja2 loop in Word:
```
{% for item in responsibilities %}
• {{ item }}
{% endfor %}
```

---

#### File 3: `templates/offer_letter_template.docx`

(To be created once you share the offer letter sample)

Use these placeholders:

```
{{ salutation }}
{{ candidate_name }}
{{ role }}
{{ department }}
{{ joining_date }}
{{ letter_date }}
{{ ctc_lpa }}                       → e.g. "6.0 LPA"
{{ ctc_annual_str }}                → e.g. "₹6,00,000"
{{ basic_monthly_str }}             → e.g. "₹20,000"
{{ hra_monthly_str }}               → e.g. "₹4,000"
{{ pf_monthly_str }}                → e.g. "₹2,400" or "N/A"
{{ special_allowance_monthly_str }} → e.g. "₹12,600"
{{ variable_annual_str }}           → e.g. "₹60,000"
{{ gross_monthly_str }}             → e.g. "₹38,600"
```

For salary table in Word, use a normal table with these placeholders in cells.

---

### Step 2: Add Company Logo

Place your company logo at:
```
assets/logo.png
```
Then add it to your Word templates in the letterhead section.

### Step 3: LibreOffice (for PDF export — Optional)

To enable PDF download, install LibreOffice:
- Windows: https://www.libreoffice.org/download/
- Mac: `brew install libreoffice`
- Linux: `sudo apt install libreoffice`

If LibreOffice is not installed, DOCX download still works perfectly.

---

## Project Structure

```
analytics_avenue_hr/
├── app.py                    ← Streamlit UI (run this)
├── modules/
│   ├── salary_calc.py        ← CTC breakup math
│   ├── ai_service.py         ← Groq API prompt parser
│   ├── pre_offer.py          ← Pre-offer letter logic
│   ├── internship.py         ← Internship letter logic
│   ├── offer_letter.py       ← Offer letter logic
│   ├── pdf_generator.py      ← docxtpl + PDF conversion
│   └── db_service.py         ← Employee data management
├── templates/                ← ⚠️ ADD YOUR .docx FILES HERE
│   ├── pre_offer_template.docx      (you create this)
│   ├── internship_template.docx     (you create this)
│   └── offer_letter_template.docx   (you create this later)
├── database/
│   └── employees.json        ← Candidate/intern data
├── output/                   ← Generated files saved here
│   └── history.json          ← Document history
├── assets/
│   └── logo.png              ← ⚠️ ADD YOUR LOGO HERE
├── .env                      ← ⚠️ ADD YOUR GROQ API KEY HERE
└── requirements.txt
```

---

## How to Use

### Generate a Letter

1. Open the app: `streamlit run app.py`
2. Select the tab: Pre-Offer / Offer Letter / Internship
3. Select candidate name from dropdown (or add new via sidebar)
4. Fill in dates and details
5. For Offer Letter: type salary prompt → click Calculate
6. Click Generate → Download DOCX or PDF

### Prompt Mode (Pre-Offer)

Type natural language:
```
Generate pre-offer for Arun – Data Analyst – joining 1st April 2026
```

### Salary Prompt (Offer Letter)

Type in the salary box:
```
6 LPA, 40% base, PF yes, 10% variable
5.5 LPA, base 45%, no PF, variable 15%
4 LPA, 40% base, PF yes
```

### Add New Candidate

Use the sidebar → Add New Person → fill details → Add Candidate

---

## Groq Models Available

| Model | Speed | Best For |
|-------|-------|----------|
| llama3-8b-8192 | Fastest | Prompt parsing (recommended) |
| llama3-70b-8192 | Slower | More complex parsing |
| mixtral-8x7b-32768 | Fast | Good accuracy |
| gemma2-9b-it | Fast | Lightweight tasks |

---

## Salary Calculation Logic

```
Basic = CTC × base_percent / 100
HRA = Basic × hra_percent / 100
PF (Employer) = Basic × 12% (if opted)
Variable = CTC × variable_percent / 100
Special Allowance = CTC - Basic - HRA - PF - Variable
Gross Monthly = (Basic + HRA + PF + Special Allowance) / 12
```

---

Built for Analytics Avenue LLP · HR Automation System
