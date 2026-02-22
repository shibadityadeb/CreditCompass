from flask import Flask, request, jsonify
from flask_cors import CORS
import pickle
import numpy as np

app = Flask(__name__)
CORS(app)

model = pickle.load(open("xgb_credit_model.pkl", "rb"))

@app.route("/predict", methods=["POST"])
def predict():
    data = request.json
    
    features = np.array([[
        data["revolving_utilization"],
        data["age"],
        data["late_30_59"],
        data["debt_ratio"],
        data["monthly_income"],
        data["open_credit_lines"],
        data["late_90"],
        data["real_estate_loans"],
        data["late_60_89"],
        data["dependents"]
    ]])
    
    prediction = model.predict_proba(features)[0][1]
    
    return jsonify({
        "default_probability": float(prediction),
        "risk_level": "High Risk" if prediction > 0.5 else "Low Risk"
    })

if __name__ == "__main__":
    app.run(debug=True)
