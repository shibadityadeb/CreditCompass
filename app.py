"""
CreditCompass - Flask REST API
Milestone 1: /predict endpoint (ML credit risk scoring)
Milestone 2: /assess endpoint (Agentic AI lending decision support)
"""
import os
import logging
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import pandas as pd
import joblib
import numpy as np
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
app = Flask(__name__)
CORS(app)  
MODEL_PATH = os.environ.get('MODEL_PATH', 'xgb_credit_model.pkl')
FEATURE_CONFIG = {
    'rev_util': {'min': 0.0, 'max': 10.0, 'type': float, 'label': 'Revolving Utilization'},
    'age': {'min': 18, 'max': 120, 'type': int, 'label': 'Age'},
    'late_30_59': {'min': 0, 'max': 50, 'type': int, 'label': 'Late 30-59 Days'},
    'debt_ratio': {'min': 0.0, 'max': 100.0, 'type': float, 'label': 'Debt Ratio'},
    'monthly_inc': {'min': 0, 'max': 10000000, 'type': float, 'label': 'Monthly Income'},
    'open_credit': {'min': 0, 'max': 100, 'type': int, 'label': 'Open Credit Lines'},
    'late_90': {'min': 0, 'max': 50, 'type': int, 'label': 'Late 90+ Days'},
    'real_estate': {'min': 0, 'max': 50, 'type': int, 'label': 'Real Estate Loans'},
    'late_60_89': {'min': 0, 'max': 50, 'type': int, 'label': 'Late 60-89 Days'},
    'dependents': {'min': 0, 'max': 20, 'type': int, 'label': 'Dependents'}
}
model = None
def load_model():
    global model
    try:
        model = joblib.load(MODEL_PATH)
        logger.info(f"Model loaded successfully from {MODEL_PATH}")
        return True
    except FileNotFoundError:
        logger.error(f"Model file not found: {MODEL_PATH}")
        return False
    except Exception as e:
        logger.error(f"Error loading model: {str(e)}")
        return False
    
def validate_input(data: dict) -> tuple[bool, str, dict]:
    sanitized = {}
    for feature, config in FEATURE_CONFIG.items():
        if feature not in data:
            return False, f"Missing required field: {config['label']}", {}
        value = data[feature]
        try:
            if config['type'] == int:
                value = int(float(value))
            else:
                value = float(value)
        except (ValueError, TypeError):
            return False, f"Invalid value for {config['label']}: must be a number", {}
        if value < config['min'] or value > config['max']:
            return False, f"{config['label']} must be between {config['min']} and {config['max']}", {}
        sanitized[feature] = value
    return True, "", sanitized

def calculate_risk_level(probability: float) -> tuple[str, str]:
    if probability > 0.7:
        return "High Risk", "high"
    elif probability > 0.4:
        return "Medium Risk", "medium"
    else:
        return "Low Risk", "low"
    
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/health', methods=['GET'])
def health_check():
    if model is None:
        load_model()
    return jsonify({
        'status': 'healthy',
        'model_loaded': model is not None
    })

@app.route('/predict', methods=['POST'])
def predict():
    try:
        if model is None:
            load_model()
        
        if model is None:
            load_model()

        if model is None:
            return jsonify({
                'success': False,
                'error': 'Model not loaded. Please contact administrator.'
            }), 503
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No input data provided. Please submit the form with all required fields.'
            }), 400
        is_valid, error_msg, sanitized_data = validate_input(data)
        if not is_valid:
            return jsonify({
                'success': False,
                'error': error_msg
            }), 400
        feature_order = list(FEATURE_CONFIG.keys())
        df = pd.DataFrame([sanitized_data])[feature_order]
        probability = float(model.predict_proba(df)[0][1])
        risk_level, risk_class = calculate_risk_level(probability)
        logger.info(f"Prediction made: probability={probability:.4f}, risk_level={risk_level}")
        return jsonify({
            'success': True,
            'risk_level': risk_level,
            'risk_class': risk_class,
            'probability': round(probability, 4),
            'message': f'Assessment complete. {risk_level} detected with {probability*100:.2f}% default probability.'
        })
    except Exception as e:
        logger.error(f"Prediction error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'An unexpected error occurred. Please try again.'
        }), 500
    
@app.route('/features', methods=['GET'])
def get_features():
    return jsonify({
        'features': FEATURE_CONFIG
    })

# ─────────────────────────────────────────────────────────────────────────────
# Milestone 2: Agentic AI Lending Decision Support
# ─────────────────────────────────────────────────────────────────────────────

# Lazy-load the agent so it does not slow down startup if langgraph is missing
_agent_loaded = False
_run_assessment = None

def _get_agent():
    """Import and cache the LangGraph agent (loaded on first use)."""
    global _agent_loaded, _run_assessment
    if not _agent_loaded:
        try:
            from backend.agent import run_assessment
            _run_assessment = run_assessment
            logger.info("LangGraph agent loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load agent: {e}")
            _run_assessment = None
        _agent_loaded = True
    return _run_assessment


@app.route('/assess', methods=['POST'])
def assess():
    """
    Milestone 2 endpoint: Agentic AI lending decision support.

    Accepts the same borrower fields as /predict (all optional — missing
    fields are handled gracefully by the agent).

    Returns a structured JSON report containing:
      - ml_prediction:  XGBoost model result
      - recommendation: Full AI lending assessment with sections:
          borrower_summary, credit_risk_analysis, lending_decision,
          decision_rationale, risk_mitigation_suggestions,
          regulatory_references, disclaimer
      - missing_fields: List of absent fields (if any)
    """
    run_assessment = _get_agent()

    if run_assessment is None:
        return jsonify({
            'success': False,
            'error': 'AI assessment service is temporarily unavailable. Please try again later.'
        }), 503

    data = request.get_json()
    if not data:
        return jsonify({
            'success': False,
            'error': 'No input data provided.'
        }), 400

    # Sanitize each field — treat empty strings as None (missing)
    borrower_data = {}
    for feature, config in FEATURE_CONFIG.items():
        value = data.get(feature)
        if value is None or value == '':
            borrower_data[feature] = None
        else:
            try:
                borrower_data[feature] = config['type'](float(value))
            except (ValueError, TypeError):
                borrower_data[feature] = None  # treat bad values as missing

    try:
        logger.info("Running AI lending assessment via LangGraph agent...")
        result = run_assessment(borrower_data)

        ml = result.get('ml_prediction', {})
        rec = result.get('recommendation', {})
        missing = result.get('missing_fields', [])

        return jsonify({
            'success': True,
            'ml_prediction': {
                'probability':     ml.get('probability', 0),
                'probability_pct': ml.get('probability_pct', 0),
                'risk_level':      ml.get('risk_level', 'Unknown'),
                'risk_class':      ml.get('risk_class', 'medium'),
                'used_defaults':   ml.get('used_defaults', []),
            },
            'recommendation': {
                'borrower_summary':           rec.get('borrower_summary', ''),
                'credit_risk_analysis':       rec.get('credit_risk_analysis', ''),
                'lending_decision':           rec.get('lending_decision', 'REVIEW'),
                'decision_rationale':         rec.get('decision_rationale', ''),
                'risk_mitigation_suggestions': rec.get('risk_mitigation_suggestions', ''),
                'regulatory_references':      rec.get('regulatory_references', ''),
                'disclaimer':                 rec.get('disclaimer', ''),
            },
            'missing_fields': missing,
        })

    except Exception as e:
        logger.error(f"Assessment error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Assessment failed. Please try again.'
        }), 500


# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'success': False, 'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'success': False, 'error': 'Internal server error'}), 500
# Model will be loaded lazily on first request

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug
    )