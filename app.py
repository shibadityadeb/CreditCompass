"""
Credit Risk Scoring System - Flask REST API
Production-ready backend with /predict endpoint
"""

import os
import logging
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import pandas as pd
import joblib
import numpy as np

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for API access

# Configuration
MODEL_PATH = os.environ.get('MODEL_PATH', 'xgb_credit_model.pkl')

# Feature configuration with validation rules
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

# Load model at startup
model = None

def load_model():
    """Load the trained XGBoost model."""
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
    """
    Validate and sanitize input data.
    Returns: (is_valid, error_message, sanitized_data)
    """
    sanitized = {}
    
    for feature, config in FEATURE_CONFIG.items():
        if feature not in data:
            return False, f"Missing required field: {config['label']}", {}
        
        value = data[feature]
        
        # Type conversion and validation
        try:
            if config['type'] == int:
                value = int(float(value))
            else:
                value = float(value)
        except (ValueError, TypeError):
            return False, f"Invalid value for {config['label']}: must be a number", {}
        
        # Range validation
        if value < config['min'] or value > config['max']:
            return False, f"{config['label']} must be between {config['min']} and {config['max']}", {}
        
        sanitized[feature] = value
    
    return True, "", sanitized


def calculate_risk_level(probability: float) -> tuple[str, str]:
    """
    Calculate risk level and color based on probability.
    Returns: (risk_level, color_class)
    """
    if probability > 0.7:
        return "High Risk", "high"
    elif probability > 0.4:
        return "Medium Risk", "medium"
    else:
        return "Low Risk", "low"


# Routes
@app.route('/')
def index():
    """Serve the main application page."""
    return render_template('index.html')


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for deployment monitoring."""
    if model is None:
        load_model()
    return jsonify({
        'status': 'healthy',
        'model_loaded': model is not None
    })


@app.route('/predict', methods=['POST'])
def predict():
    """
    Predict credit risk based on input features.
    
    Expected JSON payload:
    {
        "rev_util": float,
        "age": int,
        "late_30_59": int,
        "debt_ratio": float,
        "monthly_inc": float,
        "open_credit": int,
        "late_90": int,
        "real_estate": int,
        "late_60_89": int,
        "dependents": int
    }
    
    Returns:
    {
        "success": bool,
        "risk_level": str,
        "risk_class": str,
        "probability": float,
        "message": str
    }
    """
    try:
        # Check if model is loaded
        if model is None:
            load_model()

        if model is None:
            return jsonify({
                'success': False,
                'error': 'Model not loaded. Please contact administrator.'
            }), 503
        
        # Get JSON data
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No input data provided. Please submit the form with all required fields.'
            }), 400
        
        # Validate input
        is_valid, error_msg, sanitized_data = validate_input(data)
        
        if not is_valid:
            return jsonify({
                'success': False,
                'error': error_msg
            }), 400
        
        # Prepare data for prediction
        feature_order = list(FEATURE_CONFIG.keys())
        df = pd.DataFrame([sanitized_data])[feature_order]
        
        # Make prediction
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
    """Return feature configuration for dynamic form generation."""
    return jsonify({
        'features': FEATURE_CONFIG
    })


# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'success': False, 'error': 'Endpoint not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({'success': False, 'error': 'Internal server error'}), 500


# Initialize model on startup
# Model will be loaded lazily on first request


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug
    )