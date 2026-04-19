"""
utils/helpers.py
----------------
Helper functions for CreditCompass Milestone 2.
Handles parsing of LLM responses and building prompt context.
"""

import json


# ─────────────────────────────────────────────────────────────────────────────
# LLM Response Parser
# ─────────────────────────────────────────────────────────────────────────────

def parse_llm_response(text: str) -> dict:
    """
    Parse the structured LLM response into a dictionary of sections.

    The LLM is instructed to output specific section headers. This function
    splits the response on those headers and returns a clean dict.

    Args:
        text: Raw text response from the LLM

    Returns:
        dict with keys: borrower_summary, credit_risk_analysis,
                        lending_decision, decision_rationale,
                        risk_mitigation_suggestions, regulatory_references,
                        disclaimer, raw_response
    """
    result = {
        "borrower_summary": "",
        "credit_risk_analysis": "",
        "lending_decision": "REVIEW",   # safe default
        "decision_rationale": "",
        "risk_mitigation_suggestions": "",
        "regulatory_references": "",
        "disclaimer": (
            "This AI-generated assessment is provided for decision support "
            "purposes only. All final lending decisions must be reviewed by "
            "qualified human professionals in compliance with applicable laws."
        ),
        "raw_response": text
    }

    # Map section header keywords → result keys
    # Order matters: earlier entries take priority in case of substring overlap
    section_map = [
        ("BORROWER SUMMARY",              "borrower_summary"),
        ("CREDIT RISK ANALYSIS",          "credit_risk_analysis"),
        ("LENDING DECISION",              "lending_decision"),
        ("DECISION RATIONALE",            "decision_rationale"),
        ("RISK MITIGATION SUGGESTIONS",   "risk_mitigation_suggestions"),
        ("RISK MITIGATION",               "risk_mitigation_suggestions"),  # fallback spelling
        ("REGULATORY REFERENCES",         "regulatory_references"),
        ("DISCLAIMER",                    "disclaimer"),
    ]

    current_key = None
    current_lines: list[str] = []

    for line in text.split("\n"):
        stripped = line.strip()
        upper = stripped.upper()

        # Check if this line starts a new section
        matched = False
        for header, key in section_map:
            if upper.startswith(header):
                # Save previous section
                if current_key:
                    result[current_key] = "\n".join(current_lines).strip()
                    current_lines = []

                current_key = key

                # Grab inline content after the colon (if any)
                if ":" in stripped:
                    inline = stripped.split(":", 1)[1].strip()
                    if inline:
                        current_lines = [inline]
                else:
                    current_lines = []

                matched = True
                break

        if not matched and current_key:
            current_lines.append(line)

    # Save the last section
    if current_key:
        result[current_key] = "\n".join(current_lines).strip()

    # Normalize lending decision to one of: APPROVE / REVIEW / REJECT
    decision_raw = result.get("lending_decision", "").upper()
    if "APPROVE" in decision_raw:
        result["lending_decision"] = "APPROVE"
    elif "REJECT" in decision_raw:
        result["lending_decision"] = "REJECT"
    else:
        result["lending_decision"] = "REVIEW"

    return result


# ─────────────────────────────────────────────────────────────────────────────
# Prompt Context Builder
# ─────────────────────────────────────────────────────────────────────────────

# Human-readable labels for each feature field
FEATURE_LABELS = {
    "rev_util":    "Revolving Credit Utilization",
    "age":         "Age (years)",
    "late_30_59":  "Late Payments 30-59 days (past 2 yrs)",
    "debt_ratio":  "Debt-to-Income Ratio",
    "monthly_inc": "Monthly Income ($)",
    "open_credit": "Number of Open Credit Lines",
    "late_90":     "Late Payments 90+ days (past 2 yrs)",
    "real_estate": "Real Estate / Mortgage Loans",
    "late_60_89":  "Late Payments 60-89 days (past 2 yrs)",
    "dependents":  "Number of Dependents",
}


def build_borrower_profile_text(borrower_data: dict, missing_fields: list) -> str:
    """
    Build a human-readable borrower profile string for the prompt.
    Marks missing fields clearly.
    """
    lines = []
    for field, label in FEATURE_LABELS.items():
        if field in missing_fields or borrower_data.get(field) is None:
            lines.append(f"  - {label}: NOT PROVIDED (missing)")
        else:
            value = borrower_data[field]
            # Format nicely based on field type
            if field == "monthly_inc":
                lines.append(f"  - {label}: ${value:,.2f}")
            elif field in ("rev_util", "debt_ratio"):
                lines.append(f"  - {label}: {value:.4f}")
            else:
                lines.append(f"  - {label}: {value}")
    return "\n".join(lines)


def build_missing_data_note(missing_fields: list) -> str:
    """Return a warning note if fields are missing."""
    if not missing_fields:
        return ""
    labels = [FEATURE_LABELS.get(f, f) for f in missing_fields]
    note = (
        "⚠ MISSING DATA WARNING:\n"
        f"  The following fields were not provided: {', '.join(labels)}.\n"
        "  Default median values were used for the ML prediction.\n"
        "  The lending decision should be treated with extra caution."
    )
    return note


def build_lending_guidelines_text(rules: dict) -> str:
    """
    Extract the most relevant lending guideline sections from the rules JSON
    and format them as readable text for the prompt.
    """
    lines = []

    # Risk thresholds
    thresholds = rules.get("risk_thresholds", {})
    if thresholds:
        lines.append("Risk Decision Thresholds:")
        for level, info in thresholds.items():
            lines.append(f"  - {info.get('label', level)}: {info.get('decision', 'Review')}")

    # Debt ratio guidelines
    debt_guidelines = rules.get("debt_ratio_guidelines", {})
    if debt_guidelines:
        lines.append("\nDebt-to-Income Ratio Guidelines:")
        for tier, info in debt_guidelines.items():
            lines.append(f"  - {info['range']}: {info['assessment']}")

    # General principles (first 3)
    principles = rules.get("general_lending_principles", [])[:3]
    if principles:
        lines.append("\nGeneral Lending Principles:")
        for p in principles:
            lines.append(f"  - {p}")

    # Regulatory references (first 3)
    regs = rules.get("regulatory_references", [])[:3]
    if regs:
        lines.append("\nKey Regulatory Frameworks:")
        for reg in regs:
            lines.append(f"  - {reg['name']}: {reg['description'][:120]}...")

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Fallback Recommendation Generator
# ─────────────────────────────────────────────────────────────────────────────

def generate_fallback_recommendation(borrower_data: dict, ml_prediction: dict,
                                     missing_fields: list) -> dict:
    """
    Generate a rule-based recommendation when the LLM is unavailable.
    Uses the ML prediction and lending rules to produce a basic report.
    """
    prob = ml_prediction.get("probability", 0.5)
    risk_level = ml_prediction.get("risk_level", "Medium Risk")
    prob_pct = ml_prediction.get("probability_pct", prob * 100)

    # Determine decision
    if prob <= 0.40:
        decision = "APPROVE"
        rationale = (
            f"The ML model predicts a default probability of {prob_pct:.1f}%, which falls in the "
            f"low-risk range. The borrower demonstrates acceptable creditworthiness based on the "
            f"provided financial profile."
        )
        mitigations = [
            "- Standard loan documentation and verification required",
            "- Monitor account for first 6 months post-disbursement",
            "- Ensure loan-to-income ratio remains within policy limits",
        ]
    elif prob <= 0.70:
        decision = "REVIEW"
        rationale = (
            f"The ML model predicts a default probability of {prob_pct:.1f}%, placing this "
            f"application in the medium-risk category. Manual review by a credit officer is "
            f"recommended before proceeding."
        )
        mitigations = [
            "- Request additional income documentation (pay stubs, bank statements)",
            "- Consider reducing the approved loan amount by 20-30%",
            "- Require a co-signer or guarantor with stronger credit profile",
            "- Apply risk-adjusted interest rate to compensate for elevated risk",
        ]
    else:
        decision = "REJECT"
        rationale = (
            f"The ML model predicts a default probability of {prob_pct:.1f}%, which is in the "
            f"high-risk range. The borrower's financial profile does not meet minimum lending "
            f"standards at this time."
        )
        mitigations = [
            "- Refer borrower to a certified credit counseling service",
            "- Recommend debt reduction before reapplying in 6-12 months",
            "- Suggest a secured credit-builder product to improve credit history",
            "- Provide adverse action notice with specific reasons per FCRA requirements",
        ]

    missing_note = ""
    if missing_fields:
        labels = [FEATURE_LABELS.get(f, f) for f in missing_fields]
        missing_note = f"Note: The following fields were missing: {', '.join(labels)}. Assessment was made using default values."

    debt_ratio = borrower_data.get("debt_ratio", 0)
    income = borrower_data.get("monthly_inc", 0)
    late_90 = borrower_data.get("late_90", 0)

    summary = (
        f"The borrower has a monthly income of ${income:,.2f} with a debt-to-income ratio of "
        f"{debt_ratio:.2f}. Payment history shows {int(late_90)} instances of 90+ day late "
        f"payments. The ML model classifies this applicant as {risk_level} with a "
        f"{prob_pct:.1f}% probability of default."
    )

    analysis = (
        f"The primary risk indicators include a debt ratio of {debt_ratio:.2f} and "
        f"{int(late_90)} severe delinquency records. The XGBoost model trained on historical "
        f"credit data produces a default probability of {prob_pct:.1f}%. "
        f"{'Missing data fields add further uncertainty to this assessment. ' if missing_fields else ''}"
        f"The overall risk profile aligns with the '{risk_level}' classification."
    )

    return {
        "borrower_summary": summary + (" " + missing_note if missing_note else ""),
        "credit_risk_analysis": analysis,
        "lending_decision": decision,
        "decision_rationale": rationale,
        "risk_mitigation_suggestions": "\n".join(mitigations),
        "regulatory_references": (
            "- Equal Credit Opportunity Act (ECOA): Ensures non-discriminatory credit decisions\n"
            "- Fair Credit Reporting Act (FCRA): Governs use of credit data; requires adverse action notices\n"
            "- Truth in Lending Act (TILA): Mandates transparent disclosure of loan terms and APR"
        ),
        "disclaimer": (
            "This assessment was generated automatically (LLM unavailable) using rule-based logic "
            "and the ML model prediction. All final lending decisions must be reviewed and approved "
            "by qualified human credit professionals in compliance with ECOA, FCRA, TILA, and other "
            "applicable regulations. This does not constitute legal or financial advice."
        ),
        "raw_response": "[Fallback: LLM was not available. Rule-based assessment used.]"
    }
