import streamlit as st
import pandas as pd
import joblib

# Load trained model
model = joblib.load("xgb_credit_model.pkl")

st.set_page_config(page_title="Credit Risk System")

st.title("💳 Intelligent Credit Risk Scoring System")

st.write("Enter borrower details:")

with st.form("form"):

    rev_util = st.number_input("Revolving Utilization", 0.0, 2.0, 0.5)
    age = st.number_input("Age", 18, 100, 30)
    late_30_59 = st.number_input("Late 30-59 Days", 0, 10, 0)
    debt_ratio = st.number_input("Debt Ratio", 0.0, 5.0, 0.3)
    monthly_inc = st.number_input("Monthly Income", 0, 500000, 30000)
    open_credit = st.number_input("Open Credit Lines", 0, 20, 3)
    late_90 = st.number_input("Late 90+ Days", 0, 10, 0)
    real_estate = st.number_input("Real Estate Loans", 0, 10, 0)
    late_60_89 = st.number_input("Late 60-89 Days", 0, 10, 0)
    dependents = st.number_input("Dependents", 0, 10, 0)

    submit = st.form_submit_button("Check Risk")


if submit:

    data = pd.DataFrame([{
        "rev_util": rev_util,
        "age": age,
        "late_30_59": late_30_59,
        "debt_ratio": debt_ratio,
        "monthly_inc": monthly_inc,
        "open_credit": open_credit,
        "late_90": late_90,
        "real_estate": real_estate,
        "late_60_89": late_60_89,
        "dependents": dependents
    }])

    prob = model.predict_proba(data)[0][1]

    if prob > 0.7:
        level = "🔴 High Risk"
    elif prob > 0.4:
        level = "🟠 Medium Risk"
    else:
        level = "🟢 Low Risk"

    st.success("Result")
    st.write("Risk Level:", level)
    st.write("Default Probability:", round(prob, 4))