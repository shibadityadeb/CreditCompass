import { useState } from "react";
import axios from "axios";

export default function App() {
  const [form, setForm] = useState({
    revolving_utilization: 0.5,
    age: 30,
    late_30_59: 0,
    debt_ratio: 0.3,
    monthly_income: 30000,
    open_credit_lines: 3,
    late_90: 0,
    real_estate_loans: 0,
    late_60_89: 0,
    dependents: 0
  });

  const [result, setResult] = useState(null);

  const handleChange = (e) => {
    setForm({...form, [e.target.name]: parseFloat(e.target.value)});
  };

  const predictRisk = async () => {
    const res = await axios.post("http://127.0.0.1:5000/predict", form);
    setResult(res.data);
  };

  return (
    <div className="p-10 bg-black text-white min-h-screen">
      <h1 className="text-3xl font-bold mb-6">💳 Intelligent Credit Risk Scoring</h1>

      <div className="grid grid-cols-2 gap-4 max-w-2xl">
        <input name="revolving_utilization" onChange={handleChange} placeholder="Revolving Utilization" defaultValue={0.5} className="p-2 text-black rounded" />
        <input name="age" onChange={handleChange} placeholder="Age" defaultValue={30} className="p-2 text-black rounded" />
        <input name="late_30_59" onChange={handleChange} placeholder="Late 30-59 Days" defaultValue={0} className="p-2 text-black rounded" />
        <input name="debt_ratio" onChange={handleChange} placeholder="Debt Ratio" defaultValue={0.3} className="p-2 text-black rounded" />
        <input name="monthly_income" onChange={handleChange} placeholder="Monthly Income" defaultValue={30000} className="p-2 text-black rounded" />
        <input name="open_credit_lines" onChange={handleChange} placeholder="Open Credit Lines" defaultValue={3} className="p-2 text-black rounded" />
        <input name="late_90" onChange={handleChange} placeholder="Late 90+ Days" defaultValue={0} className="p-2 text-black rounded" />
        <input name="real_estate_loans" onChange={handleChange} placeholder="Real Estate Loans" defaultValue={0} className="p-2 text-black rounded" />
        <input name="late_60_89" onChange={handleChange} placeholder="Late 60-89 Days" defaultValue={0} className="p-2 text-black rounded" />
        <input name="dependents" onChange={handleChange} placeholder="Dependents" defaultValue={0} className="p-2 text-black rounded" />
      </div>

      <button onClick={predictRisk} className="bg-green-500 px-6 py-3 rounded mt-6 font-bold hover:bg-green-600">
        Check Risk
      </button>

      {result && (
        <div className="mt-8 p-6 bg-gray-800 rounded max-w-md">
          <p className="text-xl">Risk: <span className="font-bold">{result.risk_level}</span></p>
          <p className="text-lg mt-2">Probability: <span className="font-bold">{(result.default_probability * 100).toFixed(2)}%</span></p>
        </div>
      )}
    </div>
  );
}
