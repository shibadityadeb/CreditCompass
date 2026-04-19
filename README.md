# CreditCompass — Intelligent Credit Risk Scoring & Agentic Lending Decision Support

A college major project demonstrating ML-based credit risk scoring (Milestone 1) and an Agentic AI lending decision assistant (Milestone 2) built with Flask, LangGraph, and OpenRouter.

![Python](https://img.shields.io/badge/Python-3.11-blue.svg)
![Flask](https://img.shields.io/badge/Flask-3.0+-green.svg)
![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-purple.svg)

---

## Project Structure

```
CreditCompass/
│
├── app.py                      # Main Flask app — all API endpoints
│
├── backend/
│   ├── __init__.py
│   └── agent.py                # LangGraph 4-node agentic workflow (Milestone 2)
│
├── model/
│   ├── __init__.py
│   └── predictor.py            # Shared XGBoost model wrapper
│
├── data/
│   └── lending_rules.json      # Local lending guidelines & regulations
│
├── prompts/
│   └── lending_prompt.txt      # LLM prompt template for AI assessment
│
├── utils/
│   ├── __init__.py
│   └── helpers.py              # Response parser, prompt builders, fallback logic
│
├── templates/
│   └── index.html              # Single-page frontend (Jinja2)
│
├── static/
│   ├── css/styles.css          # Responsive UI styles
│   └── js/app.js               # Frontend JS — ML + AI assessment handlers
│
├── xgb_credit_model.pkl        # Trained XGBoost model (Milestone 1)
├── requirements.txt
├── render.yaml                 # Render free-tier deployment config
├── Procfile
└── runtime.txt
```

---

## Milestones

### Milestone 1 — ML Credit Risk Scoring
- XGBoost model trained on the Give Me Some Credit dataset
- `POST /predict` endpoint returns probability of default + risk level
- Clean web UI with animated gauge, risk badge, and detail cards

### Milestone 2 — Agentic AI Lending Decision Support
- **LangGraph workflow** with 4 sequential nodes:
  1. `check_data` — detect missing fields
  2. `predict` — run XGBoost model (supports partial input)
  3. `load_rules` — load local `data/lending_rules.json`
  4. `generate_recommendation` — call OpenRouter LLM, parse structured report
- `POST /assess` endpoint returns a full structured lending assessment
- **Missing data handling**: absent fields use dataset medians; report flags data gaps
- **Fallback**: if OpenRouter API is unavailable, rule-based recommendation is used automatically
- **Structured report sections**: Borrower Summary, Credit Risk Analysis, Lending Decision (APPROVE/REVIEW/REJECT), Decision Rationale, Risk Mitigation Suggestions, Regulatory References, Legal Disclaimer

---

## API Endpoints

### `POST /predict` — Milestone 1
Quick ML prediction.

```json
// Request (all fields required)
{
    "rev_util": 0.5,  "age": 35,      "late_30_59": 0,
    "debt_ratio": 0.3, "monthly_inc": 5000, "open_credit": 3,
    "late_90": 0,     "real_estate": 0,    "late_60_89": 0,
    "dependents": 1
}

// Response
{
    "success": true,
    "risk_level": "Low Risk",
    "risk_class": "low",
    "probability": 0.3153,
    "message": "Assessment complete. Low Risk detected with 31.53% default probability."
}
```

### `POST /assess` — Milestone 2
Full AI lending assessment via LangGraph agent.

```json
// Request (fields are optional — missing ones use defaults)
{ "age": 45, "monthly_inc": 3000, "debt_ratio": 0.65, "late_90": 2 }

// Response
{
    "success": true,
    "ml_prediction": {
        "probability": 0.72, "probability_pct": 72.0,
        "risk_level": "High Risk", "risk_class": "high",
        "used_defaults": ["rev_util", "late_30_59", ...]
    },
    "recommendation": {
        "borrower_summary": "...",
        "credit_risk_analysis": "...",
        "lending_decision": "REJECT",
        "decision_rationale": "...",
        "risk_mitigation_suggestions": "...",
        "regulatory_references": "...",
        "disclaimer": "..."
    },
    "missing_fields": ["rev_util", "late_30_59", ...]
}
```

### `GET /health`
```json
{ "status": "healthy", "model_loaded": true }
```

---

## Local Setup

```bash
# 1. Clone & enter project
git clone <repo-url>
cd "credit compasss"

# 2. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate    # macOS/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env .env.local
# Edit .env — set OPENROUTER_API_KEY (get free key at openrouter.ai)

# 5. Run
python app.py
# Open http://localhost:5000
```

> **OpenRouter API key is optional.** Without it, the system uses a built-in rule-based fallback that still produces a complete structured report. The app works end-to-end without any external API.

---

## Deployment on Render (Free)

1. Push code to GitHub
2. Go to [Render Dashboard](https://dashboard.render.com) → **New → Blueprint**
3. Connect your GitHub repo — Render detects `render.yaml` automatically
4. In Render dashboard → Environment → add secret: `OPENROUTER_API_KEY`
5. Deploy

Start command (in `render.yaml`):
```
gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --threads 2
```

---

## Input Features

| Field | Type | Range | Description |
|-------|------|-------|-------------|
| `rev_util` | float | 0–10 | Revolving credit utilization ratio |
| `age` | int | 18–120 | Borrower's age in years |
| `late_30_59` | int | 0–50 | Times 30–59 days late (past 2 yrs) |
| `debt_ratio` | float | 0–100 | Debt-to-income ratio |
| `monthly_inc` | float | 0–10M | Gross monthly income ($) |
| `open_credit` | int | 0–100 | Number of open credit lines |
| `late_90` | int | 0–50 | Times 90+ days late (past 2 yrs) |
| `real_estate` | int | 0–50 | Real estate / mortgage loans |
| `late_60_89` | int | 0–50 | Times 60–89 days late (past 2 yrs) |
| `dependents` | int | 0–20 | Number of dependents |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Flask 3, Python 3.11 |
| ML Model | XGBoost (trained, `.pkl`) |
| Agent Framework | LangGraph |
| LLM | OpenRouter (Mistral-7B-Instruct free tier) |
| Knowledge Context | Local JSON (no vector DB needed) |
| Frontend | Vanilla HTML/CSS/JS |
| Deployment | Render (free tier) |
