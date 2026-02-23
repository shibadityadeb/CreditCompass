# CreditCompass - Intelligent Credit Risk Scoring System

A production-ready web application for credit risk assessment powered by XGBoost machine learning.

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-3.0+-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## Features

- **ML-Powered Predictions**: XGBoost model trained on historical credit data
- **REST API**: Clean `/predict` endpoint accepting JSON input
- **Modern UI**: Responsive dashboard with gradient design and animations
- **Real-time Validation**: Client and server-side input validation
- **Production Ready**: Health checks, CORS support, Render & Vercel ready

## Project Structure

```
CreditCompass/
├── app.py                  # Flask REST API backend
├── xgb_credit_model.pkl    # Trained XGBoost model
├── requirements.txt        # Python dependencies
├── Procfile               # Render deployment
├── render.yaml            # Render blueprint config
├── vercel.json            # Vercel deployment config
├── .env.example           # Environment variables template
├── .gitignore            # Git ignore rules
├── templates/
│   └── index.html         # Main application page
├── static/
│   ├── css/
│   │   └── styles.css     # Modern responsive styles
│   └── js/
│       └── app.js         # Frontend logic & API calls
└── api/
    └── index.py           # Vercel serverless entry point
```

## API Endpoints

### `POST /predict`

Predict credit risk for a borrower.

**Request:**
```json
{
    "rev_util": 0.5,
    "age": 35,
    "late_30_59": 0,
    "debt_ratio": 0.3,
    "monthly_inc": 5000,
    "open_credit": 3,
    "late_90": 0,
    "real_estate": 1,
    "late_60_89": 0,
    "dependents": 2
}
```

**Response:**
```json
{
    "success": true,
    "risk_level": "Low Risk",
    "risk_class": "low",
    "probability": 0.1234,
    "message": "Assessment complete. Low Risk detected with 12.34% default probability."
}
```

### `GET /health`

Health check endpoint for monitoring.

**Response:**
```json
{
    "status": "healthy",
    "model_loaded": true
}
```

## Local Development

### Prerequisites

- Python 3.11+
- pip or conda

### Setup

1. **Clone the repository:**
```bash
git clone https://github.com/yourusername/CreditCompass.git
cd CreditCompass
```

2. **Create virtual environment:**
```bash
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
.venv\Scripts\activate     # Windows
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Set environment variables:**
```bash
cp .env.example .env
```

5. **Run the application:**
```bash
python app.py
```

6. **Open in browser:**
```
http://localhost:5000
```

## Cloud Deployment

### Render (Free Tier)

**Option 1: One-Click Deploy with Blueprint**

1. Fork this repository to your GitHub
2. Go to [Render Dashboard](https://dashboard.render.com)
3. Click **New** → **Blueprint**
4. Connect your GitHub repo
5. Render auto-detects `render.yaml` and deploys

**Option 2: Manual Setup**

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click **New** → **Web Service**
3. Connect your GitHub repository
4. Configure:
   - **Name**: `creditcompass`
   - **Region**: Oregon (Free)
   - **Branch**: `main`
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --threads 2`
   - **Instance Type**: **Free**
5. Click **Create Web Service**

> **Note**: Free tier spins down after 15 minutes of inactivity. First request after idle may take 30-60 seconds.

### Vercel (Free Tier)

1. Install Vercel CLI:
```bash
npm i -g vercel
```

2. Login to Vercel:
```bash
vercel login
```

3. Deploy from project root:
```bash
vercel
```

4. For production deployment:
```bash
vercel --prod
```

**Or deploy via Dashboard:**
1. Go to [Vercel](https://vercel.com)
2. Click **Add New** → **Project**
3. Import your GitHub repository
4. Vercel auto-detects `vercel.json`
5. Click **Deploy**

> **Note**: Vercel free tier has 100GB bandwidth/month and 10-second function timeout.

### Railway

1. Create a new project on [Railway](https://railway.app)
2. Connect your GitHub repository
3. Railway auto-detects the `Procfile`
4. Deploy automatically

### AWS (Elastic Beanstalk)

1. **Install EB CLI:**
```bash
pip install awsebcli
```

2. **Initialize EB:**
```bash
eb init -p python-3.11 creditcompass
```

3. **Create environment:**
```bash
eb create creditcompass-prod
```

4. **Deploy:**
```bash
eb deploy
```

### VPS (Ubuntu)

1. **Clone repository:**
```bash
git clone https://github.com/yourusername/CreditCompass.git
cd CreditCompass
```

2. **Install dependencies:**
```bash
sudo apt update
sudo apt install python3-pip python3-venv nginx
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

3. **Create systemd service:**
```bash
sudo nano /etc/systemd/system/creditcompass.service
```

```ini
[Unit]
Description=CreditCompass Credit Risk API
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/CreditCompass
Environment="PATH=/var/www/CreditCompass/.venv/bin"
ExecStart=/var/www/CreditCompass/.venv/bin/gunicorn --workers 2 --bind unix:creditcompass.sock app:app

[Install]
WantedBy=multi-user.target
```

4. **Configure Nginx:**
```bash
sudo nano /etc/nginx/sites-available/creditcompass
```

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        include proxy_params;
        proxy_pass http://unix:/var/www/CreditCompass/creditcompass.sock;
    }

    location /static {
        alias /var/www/CreditCompass/static;
    }
}
```

5. **Enable and start:**
```bash
sudo ln -s /etc/nginx/sites-available/creditcompass /etc/nginx/sites-enabled
sudo systemctl start creditcompass
sudo systemctl enable creditcompass
sudo systemctl restart nginx
```

## Input Features

| Feature | Type | Range | Description |
|---------|------|-------|-------------|
| `rev_util` | float | 0.0 - 10.0 | Revolving credit utilization ratio |
| `age` | int | 18 - 120 | Borrower's age in years |
| `late_30_59` | int | 0 - 50 | Times 30-59 days late (last 2 years) |
| `debt_ratio` | float | 0.0 - 100.0 | Debt-to-income ratio |
| `monthly_inc` | float | 0 - 10M | Gross monthly income ($) |
| `open_credit` | int | 0 - 100 | Number of open credit lines |
| `late_90` | int | 0 - 50 | Times 90+ days late (last 2 years) |
| `real_estate` | int | 0 - 50 | Number of real estate loans |
| `late_60_89` | int | 0 - 50 | Times 60-89 days late (last 2 years) |
| `dependents` | int | 0 - 20 | Number of dependents |

## Risk Classification

| Probability | Risk Level | Color |
|-------------|------------|-------|
| 0% - 40% | Low Risk | Green |
| 40% - 70% | Medium Risk | Orange |
| 70% - 100% | High Risk | Red |

## Security Considerations

- Server-side input validation with type checking and range limits
- CORS enabled for API access control
- No sensitive data stored or logged
- Exception handling to prevent information leakage
- Prepared for HTTPS deployment (configure at reverse proxy level)

## License

MIT License - see LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request
