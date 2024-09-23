from website import create_app
from flask import Flask, request, jsonify, session, url_for
import os
from dotenv import load_dotenv
import requests
import stripe
import jwt as pyjwt  # Import PyJWT under an alias
from datetime import datetime, timedelta
import logging

load_dotenv()

app = create_app()

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
API_URL = os.getenv('API_URL')


# webhook endpoint for handling Stripe events
# Webhook endpoint for handling Stripe events
@app.route('/stripe/webhook', methods=['POST'])
def stripe_webhook():
    logging.info("Stripe webhook triggered.")
    
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')
    endpoint_secret = os.getenv('STRIPE_WEBHOOK_SECRET')

    try:
        # Construct the event from the Stripe webhook
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
        logging.info("Stripe event constructed successfully.")
    except ValueError as e:
        logging.error("Invalid payload from Stripe.")
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError as e:
        logging.error("Invalid signature verification from Stripe.")
        return jsonify({'error': 'Invalid signature'}), 400

    # Handle the checkout session completed event
    if event['type'] == 'checkout.session.completed':
        session_data = event['data']['object']
        customer_email = session_data.get('customer_details', {}).get('email')
        logging.info(f"Checkout session completed for {customer_email}.")

        # Redirect to the route that updates the premium status
        return jsonify({
            'status': 'success',
            'redirect_url': url_for('update_premium_status', email=customer_email)
        }), 200

    logging.info("Stripe webhook processed successfully.")
    return jsonify({'status': 'success'}), 200


# Route to update the premium status in the database
@app.route('/update-premium', methods=['POST'])
def update_premium_status():
    data = request.get_json()
    user_email = data.get('email')

    if not user_email:
        logging.error("No email provided to update premium status.")
        return jsonify({'error': 'No email provided'}), 400

    logging.info(f"Attempting to update premium status for {user_email}.")

    # Use the existing access token stored in session
    access_token = session.get('access_token')
    if not access_token:
        logging.error("No access token available in session.")
        return jsonify({'error': 'No access token available'}), 401

    # Call your API to grant the user premium status
    headers = {'Authorization': f'Bearer {access_token}'}
    user_search_url = f"{API_URL}/users/search"
    response = requests.get(user_search_url, params={'email': user_email}, headers=headers)

    if response.status_code == 200:
        user_data = response.json()
        user_id = user_data.get('id')

        if user_id:
            logging.info(f"User ID {user_id} found. Attempting to grant premium status.")
            user_update_url = f"{API_URL}/user/{user_id}/premium/grant"
            grant_response = requests.put(user_update_url, headers=headers)

            if grant_response.status_code == 200:
                logging.info(f"Premium status successfully granted for user ID {user_id}.")
                return jsonify({'status': 'Premium status granted'}), 200
            else:
                logging.error(f"Failed to grant premium status for user ID {user_id}. Response: {grant_response.text}")
                return jsonify({'error': 'Failed to grant premium status'}), 500
        else:
            logging.error(f"User ID not found for {user_email}.")
            return jsonify({'error': 'User not found'}), 404
    else:
        logging.error(f"Failed to retrieve user info for {user_email}. Response: {response.text}")
        return jsonify({'error': 'Failed to retrieve user info'}), 500




if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, use_reloader=False, host="0.0.0.0", port=port)