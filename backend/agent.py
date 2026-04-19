"""
backend/agent.py
----------------
LangGraph-based Agentic AI Lending Decision Support Workflow (Milestone 2).

The workflow has 4 nodes that execute sequentially:
  1. check_data          – Validate input and identify missing fields
  2. predict             – Run the XGBoost ML model
  3. load_rules          – Load lending guidelines from local JSON file
  4. generate_recommendation – Call the LLM via OpenRouter to produce
                              a structured lending assessment report

If the OpenRouter API is unavailable or the key is missing, the workflow
falls back to a rule-based recommendation built in utils/helpers.py.
"""

import os
import json
import logging
import requests
from typing import TypedDict, Optional

from langgraph.graph import StateGraph, END

# Import shared predictor and helpers
# (sys.path manipulation is handled at import time by app.py being at root)
from model.predictor import predict as ml_predict
from utils.helpers import (
    parse_llm_response,
    build_borrower_profile_text,
    build_missing_data_note,
    build_lending_guidelines_text,
    generate_fallback_recommendation,
)

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Paths
# ─────────────────────────────────────────────────────────────────────────────

BASE_DIR = os.path.dirname(os.path.dirname(__file__))  # project root
RULES_PATH = os.path.join(BASE_DIR, "data", "lending_rules.json")
PROMPT_PATH = os.path.join(BASE_DIR, "prompts", "lending_prompt.txt")


# ─────────────────────────────────────────────────────────────────────────────
# Shared Agent State
# ─────────────────────────────────────────────────────────────────────────────

class LendingState(TypedDict):
    """
    State shared across all LangGraph nodes.
    Each node receives the full state and returns a partial update dict.
    """
    borrower_data: dict            # Raw input from the frontend form
    missing_fields: list           # Fields absent or None in borrower_data
    ml_prediction: dict            # Output from the XGBoost model
    lending_rules: dict            # Loaded from data/lending_rules.json
    recommendation: dict           # Final structured assessment
    error: str                     # Non-fatal error messages (empty = OK)


# ─────────────────────────────────────────────────────────────────────────────
# Node 1: check_data
# ─────────────────────────────────────────────────────────────────────────────

def check_data_node(state: LendingState) -> dict:
    """
    Identify which of the 10 expected borrower fields are missing or None.
    This list is passed downstream so the LLM can mention the data gaps.
    """
    required = [
        "rev_util", "age", "late_30_59", "debt_ratio", "monthly_inc",
        "open_credit", "late_90", "real_estate", "late_60_89", "dependents"
    ]
    data = state.get("borrower_data", {})
    missing = [f for f in required if data.get(f) is None]

    if missing:
        logger.info(f"[check_data] Missing fields detected: {missing}")
    else:
        logger.info("[check_data] All fields present.")

    return {"missing_fields": missing}


# ─────────────────────────────────────────────────────────────────────────────
# Node 2: predict
# ─────────────────────────────────────────────────────────────────────────────

def predict_node(state: LendingState) -> dict:
    """
    Run the trained XGBoost model on the borrower data.
    Missing fields are filled with dataset medians by model/predictor.py.
    """
    try:
        prediction = ml_predict(state["borrower_data"])
        logger.info(
            f"[predict] probability={prediction['probability']:.4f}, "
            f"risk={prediction['risk_level']}"
        )
        return {"ml_prediction": prediction, "error": ""}
    except Exception as e:
        logger.error(f"[predict] ML prediction failed: {e}")
        # Provide a neutral fallback so downstream nodes can still run
        return {
            "ml_prediction": {
                "probability": 0.5,
                "probability_pct": 50.0,
                "risk_level": "Unknown",
                "risk_class": "medium",
                "used_defaults": [],
            },
            "error": f"ML prediction failed: {str(e)}"
        }


# ─────────────────────────────────────────────────────────────────────────────
# Node 3: load_rules
# ─────────────────────────────────────────────────────────────────────────────

def load_rules_node(state: LendingState) -> dict:
    """
    Load the lending guidelines from data/lending_rules.json.
    Falls back to a minimal inline rules dict if the file is unavailable.
    """
    try:
        with open(RULES_PATH, "r") as f:
            rules = json.load(f)
        logger.info("[load_rules] Lending rules loaded successfully.")
        return {"lending_rules": rules}
    except Exception as e:
        logger.warning(f"[load_rules] Could not load rules file: {e}. Using defaults.")
        return {
            "lending_rules": {
                "risk_thresholds": {
                    "low_risk":    {"label": "Low Risk",    "decision": "Approve"},
                    "medium_risk": {"label": "Medium Risk", "decision": "Review"},
                    "high_risk":   {"label": "High Risk",   "decision": "Reject"},
                },
                "general_lending_principles": [
                    "Assess borrower's ability to repay based on income and debt",
                    "All decisions must comply with ECOA and FCRA",
                ],
                "regulatory_references": [
                    {"name": "ECOA", "description": "Prohibits credit discrimination"},
                    {"name": "FCRA", "description": "Governs use of credit information"},
                ],
            }
        }


# ─────────────────────────────────────────────────────────────────────────────
# Node 4: generate_recommendation
# ─────────────────────────────────────────────────────────────────────────────

def _load_prompt_template() -> str:
    """Load prompt template from file, return a hardcoded fallback if missing."""
    try:
        with open(PROMPT_PATH, "r") as f:
            return f.read()
    except Exception:
        # Inline fallback template
        return (
            "You are a credit risk analyst. Review this loan application and provide a "
            "structured assessment.\n\nBORROWER PROFILE:\n{borrower_profile}\n\n"
            "ML PREDICTION:\n- Default Probability: {probability_pct}%\n"
            "- Risk Level: {risk_level}\n\n{missing_data_note}\n\n"
            "GUIDELINES:\n{lending_guidelines}\n\n"
            "Write the assessment using these exact headers:\n"
            "BORROWER SUMMARY:\nCREDIT RISK ANALYSIS:\nLENDING DECISION:\n"
            "DECISION RATIONALE:\nRISK MITIGATION SUGGESTIONS:\n"
            "REGULATORY REFERENCES:\nDISCLAIMER:"
        )


def _call_openrouter(prompt: str) -> str:
    """
    Call the OpenRouter API to get an LLM response.
    Uses the free mistral-7b-instruct model.

    Raises:
        ValueError if the API key is not configured
        requests.HTTPError on API errors
    """
    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY environment variable is not set.")

    payload = {
        "model": "mistralai/mistral-7b-instruct:free",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are an expert credit risk analyst. "
                    "Provide professional, structured, and concise lending assessments. "
                    "Follow the output format exactly as instructed."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "max_tokens": 1200,
        "temperature": 0.3,  # low temperature = more consistent, deterministic output
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://creditcompass.onrender.com",
        "X-Title": "CreditCompass AI Lending Assistant",
    }

    response = requests.post(
        url="https://openrouter.ai/api/v1/chat/completions",
        headers=headers,
        json=payload,
        timeout=45,  # OpenRouter free tier can be slow
    )
    response.raise_for_status()

    data = response.json()
    return data["choices"][0]["message"]["content"]


def generate_recommendation_node(state: LendingState) -> dict:
    """
    Build the prompt from state, call the LLM, and parse the structured response.
    Falls back to rule-based assessment if LLM is unavailable.
    """
    borrower_data = state.get("borrower_data", {})
    missing_fields = state.get("missing_fields", [])
    ml_prediction = state.get("ml_prediction", {})
    lending_rules = state.get("lending_rules", {})

    # Build prompt context strings
    borrower_profile = build_borrower_profile_text(borrower_data, missing_fields)
    missing_note = build_missing_data_note(missing_fields)
    guidelines = build_lending_guidelines_text(lending_rules)

    # Fill prompt template
    template = _load_prompt_template()
    prompt = template.format(
        borrower_profile=borrower_profile,
        probability_pct=ml_prediction.get("probability_pct", "N/A"),
        risk_level=ml_prediction.get("risk_level", "Unknown"),
        missing_data_note=missing_note,
        lending_guidelines=guidelines,
    )

    # Attempt LLM call
    try:
        logger.info("[generate_recommendation] Calling OpenRouter LLM...")
        raw_response = _call_openrouter(prompt)
        recommendation = parse_llm_response(raw_response)
        logger.info(
            f"[generate_recommendation] LLM response received. "
            f"Decision: {recommendation.get('lending_decision')}"
        )
    except ValueError as e:
        # API key not set — use fallback silently
        logger.warning(f"[generate_recommendation] LLM unavailable: {e}. Using fallback.")
        recommendation = generate_fallback_recommendation(
            borrower_data, ml_prediction, missing_fields
        )
    except Exception as e:
        # Network / API error — use fallback
        logger.error(f"[generate_recommendation] LLM call failed: {e}. Using fallback.")
        recommendation = generate_fallback_recommendation(
            borrower_data, ml_prediction, missing_fields
        )

    return {"recommendation": recommendation}


# ─────────────────────────────────────────────────────────────────────────────
# Build the LangGraph Workflow
# ─────────────────────────────────────────────────────────────────────────────

def _build_graph() -> StateGraph:
    """
    Construct and compile the LangGraph workflow.

    Graph topology:
      check_data → predict → load_rules → generate_recommendation → END
    """
    workflow = StateGraph(LendingState)

    workflow.add_node("check_data",              check_data_node)
    workflow.add_node("predict",                 predict_node)
    workflow.add_node("load_rules",              load_rules_node)
    workflow.add_node("generate_recommendation", generate_recommendation_node)

    workflow.set_entry_point("check_data")
    workflow.add_edge("check_data",              "predict")
    workflow.add_edge("predict",                 "load_rules")
    workflow.add_edge("load_rules",              "generate_recommendation")
    workflow.add_edge("generate_recommendation", END)

    return workflow.compile()


# Compiled graph — imported by app.py
agent_graph = _build_graph()
logger.info("[agent] LangGraph lending assessment workflow compiled successfully.")


# ─────────────────────────────────────────────────────────────────────────────
# Public Entry Point
# ─────────────────────────────────────────────────────────────────────────────

def run_assessment(borrower_data: dict) -> dict:
    """
    Run the full lending assessment workflow for a borrower.

    Args:
        borrower_data: dict with borrower fields (partial input is allowed)

    Returns:
        dict with:
            ml_prediction  – XGBoost model output
            recommendation – Structured AI lending assessment
            missing_fields – List of fields that were absent
            error          – Error message if any step failed (empty = OK)
    """
    initial_state: LendingState = {
        "borrower_data":  borrower_data,
        "missing_fields": [],
        "ml_prediction":  {},
        "lending_rules":  {},
        "recommendation": {},
        "error":          "",
    }

    result = agent_graph.invoke(initial_state)

    return {
        "ml_prediction":  result.get("ml_prediction", {}),
        "recommendation": result.get("recommendation", {}),
        "missing_fields": result.get("missing_fields", []),
        "error":          result.get("error", ""),
    }
