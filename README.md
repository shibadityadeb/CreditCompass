# CreditCompass — AI Credit Risk & Lending Decision Platform

A college major project: ML credit risk scoring (Milestone 1) + Agentic AI lending decision support (Milestone 2).

**Stack:** Flask · XGBoost · LangGraph · OpenRouter (Mistral-7B free) · Tailwind CSS · Render

**Project Report (PDF):** [reports/CreditCompass.pdf](reports/CreditCompass.pdf)

---

## How the Data Flows

### Milestone 1 — `/predict` (quick ML scoring)

```
User fills form
       │
       ▼
Browser (app.js)  ──POST /predict──►  Flask (app.py)
                                             │
                                             ▼
                                    validate_input()
                                             │
                                             ▼
                                    xgb_credit_model.pkl
                                    model.predict_proba()
                                             │
                                             ▼
                                    { probability, risk_level,
                                      risk_class, message }
                                             │
       ◄──────────────────────────────────────┘
       │
       ▼
Display gauge + risk badge
(animates from 0 → probability%)
```

---

### Milestone 2 — `/assess` (agentic AI decision support)

```
User clicks "Get Full AI Lending Assessment"
       │
       ▼
Browser (app.js)  ──POST /assess──►  Flask (app.py)
                                             │
                                     sanitize fields
                                     (None for missing)
                                             │
                                             ▼
                               backend/agent.py → run_assessment()
                                             │
                         ┌───────────────────┴──────────────────────┐
                         │        LangGraph StateGraph               │
                         │                                           │
                         │  Node 1: check_data_node                  │
                         │    → scans 10 fields for None             │
                         │    → returns missing_fields: [...]        │
                         │              │                            │
                         │              ▼                            │
                         │  Node 2: predict_node                     │
                         │    → model/predictor.py                   │
                         │    → fills missing with dataset medians   │
                         │    → returns ml_prediction dict           │
                         │              │                            │
                         │              ▼                            │
                         │  Node 3: load_rules_node                  │
                         │    → reads data/lending_rules.json        │
                         │    → returns full rules dict              │
                         │              │                            │
                         │              ▼                            │
                         │  Node 4: generate_recommendation_node     │
                         │    → builds prompt from:                  │
                         │       • borrower profile                  │
                         │       • ML prediction                     │
                         │       • missing fields note               │
                         │       • lending rules                     │
                         │    → reads prompts/lending_prompt.txt     │
                         │    → calls OpenRouter API (Mistral-7B)    │
                         │    → if API fails → fallback in           │
                         │       utils/helpers.py                    │
                         │    → parse_llm_response() extracts        │
                         │       7 structured sections               │
                         └───────────────────────────────────────────┘
                                             │
                                             ▼
                              { ml_prediction, recommendation,
                                missing_fields }
                                             │
       ◄─────────────────────────────────────┘
       │
       ▼
Display full AI report:
  • Decision banner (APPROVE / REVIEW / REJECT)
  • Missing data alert (if applicable)
  • 6 section cards rendered from recommendation dict
```

---

## Project Structure

```
CreditCompass/
│
├── app.py                      # Flask app — /predict + /assess endpoints
│
├── backend/
│   └── agent.py                # LangGraph 4-node workflow (Milestone 2)
│
├── model/
│   └── predictor.py            # XGBoost model wrapper (shared by both endpoints)
│
├── data/
│   └── lending_rules.json      # Local lending guidelines + 6 regulations
│
├── prompts/
│   └── lending_prompt.txt      # LLM prompt template (loaded by Node 4)
│
├── utils/
│   └── helpers.py              # parse_llm_response(), prompt builders,
│                               # generate_fallback_recommendation()
│
├── templates/
│   └── index.html              # Frontend (Tailwind CSS CDN + custom CSS)
│
├── static/
│   ├── css/styles.css          # Custom animations, gauge, spinner, risk badge
│   └── js/app.js               # Two IIFE modules: M1 (/predict) + M2 (/assess)
│
├── xgb_credit_model.pkl        # Trained XGBoost model binary
├── requirements.txt            # Python dependencies
├── render.yaml                 # Render free-tier deployment blueprint
├── Procfile                    # gunicorn start command
└── runtime.txt                 # python-3.11.0
```

---

## API Endpoints

### `POST /predict` — Milestone 1 (all fields required)

```json
// Request
{
  "rev_util": 0.5,   "age": 35,         "late_30_59": 0,
  "debt_ratio": 0.3, "monthly_inc": 5000,"open_credit": 3,
  "late_90": 0,      "real_estate": 0,   "late_60_89": 0,
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

### `POST /assess` — Milestone 2 (fields are optional — missing ones use defaults)

```json
// Request (partial example — missing fields handled gracefully)
{ "age": 52, "monthly_inc": 3200, "debt_ratio": 0.68, "late_90": 2 }

// Response
{
  "success": true,
  "ml_prediction": {
    "probability": 0.72,
    "probability_pct": 72.0,
    "risk_level": "High Risk",
    "risk_class": "high",
    "used_defaults": ["rev_util", "late_30_59", "open_credit", "real_estate", "late_60_89", "dependents"]
  },
  "recommendation": {
    "borrower_summary":            "...",
    "credit_risk_analysis":        "...",
    "lending_decision":            "REJECT",
    "decision_rationale":          "...",
    "risk_mitigation_suggestions": "...",
    "regulatory_references":       "...",
    "disclaimer":                  "..."
  },
  "missing_fields": ["rev_util", "late_30_59", ...]
}
```

### `GET /health`
```json
{ "status": "healthy", "model_loaded": true }
```

---

## Feature Defaults (used when fields are missing in /assess)

| Field | Default | Source |
|-------|---------|--------|
| `rev_util` | 0.154 | Dataset median |
| `age` | 52 | Dataset median |
| `late_30_59` | 0 | Dataset median |
| `debt_ratio` | 0.336 | Dataset median |
| `monthly_inc` | 5400.0 | Dataset median |
| `open_credit` | 8 | Dataset median |
| `late_90` | 0 | Dataset median |
| `real_estate` | 1 | Dataset median |
| `late_60_89` | 0 | Dataset median |
| `dependents` | 0 | Dataset median |

---

## LangGraph Agent Nodes

| Node | File | What it does |
|------|------|-------------|
| `check_data` | `backend/agent.py` | Scans input dict for None values → builds `missing_fields` list |
| `predict` | `model/predictor.py` | Runs XGBoost; fills missing fields with medians |
| `load_rules` | `data/lending_rules.json` | Loads risk thresholds, debt ratio bands, regulations |
| `generate_recommendation` | `utils/helpers.py` + OpenRouter | Builds prompt → calls Mistral-7B → parses 7-section response |

---

## Local Setup

```bash
git clone <repo>
cd "credit compasss"

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Edit .env — set OPENROUTER_API_KEY (get free key at openrouter.ai)
# Without key, falls back to rule-based assessment automatically

PORT=5001 python app.py
# Open http://localhost:5001
```

## Deploy on Render

1. Push to GitHub
2. Render Dashboard → New → Blueprint → connect repo (`render.yaml` auto-detected)
3. Environment tab → add secret: `OPENROUTER_API_KEY`
4. Deploy — start command: `gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --threads 2`

---

## Risk Thresholds

| Probability | Risk Level | Decision |
|-------------|------------|---------|
| 0% – 40% | Low Risk | APPROVE |
| 40% – 70% | Medium Risk | REVIEW |
| 70% – 100% | High Risk | REJECT |
