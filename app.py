from website import create_app
from flask import Flask, request, jsonify, session, url_for, redirect, flash
import os
from dotenv import load_dotenv
import requests
import stripe
import logging

# Load environment variables
load_dotenv()

app = create_app()

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Stripe API setup
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
API_URL = os.getenv('API_URL')

# Ensure the secret key is set for session management
app.secret_key = os.getenv('SECRET_KEY', 'your_default_secret_key')
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = True

# Helper function to get the user's JWT token from the session
def get_headers():
    token = session.get('access_token')
    if token:
        return {'Authorization': f'Bearer {token}'}
    else:
        logger.error("No user access token found in session")
        return None

# Webhook endpoint for handling Stripe events
@app.route('/stripe/webhook', methods=['POST'])
def stripe_webhook():
    logger.info("Stripe webhook triggered.")

    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')
    endpoint_secret = os.getenv('STRIPE_WEBHOOK_SECRET')

    try:
        # Construct the event from the Stripe webhook
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
        logger.info("Stripe event constructed successfully.")
    except ValueError as e:
        logger.error("Invalid payload from Stripe.", exc_info=True)
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError as e:
        logger.error("Invalid signature verification from Stripe.", exc_info=True)
        return jsonify({'error': 'Invalid signature'}), 400

    # Handle the checkout session completed event
    if event['type'] == 'checkout.session.completed':
        session_data = event['data']['object']
        customer_email = session_data.get('customer_details', {}).get('email')
        logger.info(f"Checkout session completed for {customer_email}.")

        # Call the function to grant premium status using the customer's email
        grant_premium_status(customer_email)

    logger.info("Stripe webhook processed successfully.")
    return jsonify({'status': 'success'}), 200

# Function to grant premium status to the user after successful payment
def grant_premium_status(customer_email):
    logger.info(f"Attempting to grant premium status for {customer_email}.")
    
    # Retrieve user info from your API by their email
    headers = get_headers()
    if not headers:
        logger.error("Unable to grant premium status due to missing user token.")
        return
    
    # Search for the user by email using your API
    user_search_url = f"{API_URL}/users/search"
    response = requests.get(user_search_url, params={'email': customer_email}, headers=headers)

    if response.status_code == 200:
        user_data = response.json()
        user_id = user_data.get('id')

        if user_id:
            logger.info(f"User ID {user_id} found. Attempting to grant premium status.")

            # Make a request to your API to grant the user premium status
            user_update_url = f"{API_URL}/user/{user_id}/premium/grant"
            grant_response = requests.put(user_update_url, headers=headers)

            if grant_response.status_code == 200:
                logger.info(f"Premium status successfully granted for user ID {user_id}.")
            else:
                logger.error(f"Failed to grant premium status for user ID {user_id}. Response: {grant_response.text}")
        else:
            logger.error(f"User ID not found for email {customer_email}.")
    else:
        logger.error(f"Failed to retrieve user info for {customer_email}. Response: {response.text}")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, use_reloader=False, host="0.0.0.0", port=port)
