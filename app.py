from website import create_app
from flask import Flask, request, jsonify
import os
from dotenv import load_dotenv
import requests
import logging

# Load environment variables
load_dotenv()

# Create the Flask app instance
app = create_app()

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Ensure the secret key is set for session management
app.secret_key = os.getenv('SECRET_KEY', 'your_default_secret_key')
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = True




if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, use_reloader=False, host="0.0.0.0", port=port)
