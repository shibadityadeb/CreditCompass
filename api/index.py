"""
CreditCompass - Vercel Serverless Function Entry Point
This file wraps the Flask app for Vercel's serverless deployment
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the Flask app
from app import app

# Vercel expects the app to be named 'app' or 'handler'
# The Flask app is already named 'app', so this works directly
