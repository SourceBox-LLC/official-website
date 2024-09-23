from website import create_app
from flask import Flask, request, jsonify, session
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

# Webhook endpoint for handling Stripe events
@app.route('/stripe/webhook', methods=['POST'])
def stripe_payment_confirmation():
    logger.info("Stripe webhook triggered.")
    
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')
    endpoint_secret = os.getenv('STRIPE_WEBHOOK_SECRET')

    logger.debug(f"Payload received: {payload}")
    logger.debug(f"Stripe-Signature received: {sig_header}")

    try:
        # Construct the event from the Stripe webhook
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
        logger.info("Stripe event constructed successfully.")
    except ValueError as e:
        logger.error("Invalid payload from Stripe.")
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError as e:
        logger.error("Invalid signature verification from Stripe.")
        return jsonify({'error': 'Invalid signature'}), 400

    # Handle the checkout session completed event
    if event['type'] == 'checkout.session.completed':
        session_data = event['data']['object']
        customer_email = session_data['customer_details']['email']

        logger.info(f"Checkout session completed for {customer_email}.")

        # Retrieve the access token stored in the session
        access_token = session.get('access_token')
        if not access_token:
            logger.error("No access token available in session.")
            return jsonify({'error': 'No access token available'}), 401

        headers = {'Authorization': f'Bearer {access_token}'}
        user_search_url = f"{API_URL}/users/search"

        # Use the GET request to search for the user by email
        logger.debug(f"Sending GET request to search user: {user_search_url} with email {customer_email}")
        response = requests.get(user_search_url, params={'email': customer_email}, headers=headers)

        if response.status_code == 200:
            logger.info(f"User search successful for {customer_email}.")
            user_data = response.json()
            user_id = user_data.get('id')

            if user_id:
                logger.debug(f"User ID found: {user_id}. Attempting to grant premium status.")
                # Grant premium status to the user
                user_update_url = f"{API_URL}/user/{user_id}/premium/grant"
                grant_response = requests.put(user_update_url, headers=headers)

                if grant_response.status_code == 200:
                    logger.info(f"Premium status granted for user ID {user_id}.")
                    return jsonify({'status': 'Premium status granted'}), 200
                else:
                    logger.error(f"Failed to grant premium status for user ID {user_id}. Response: {grant_response.text}")
                    return jsonify({'error': 'Failed to grant premium status'}), 500
            else:
                logger.error(f"User ID not found for {customer_email}.")
                return jsonify({'error': 'User not found'}), 404
        else:
            logger.error(f"Failed to retrieve user info for {customer_email}. Response: {response.text}")
            return jsonify({'error': 'Failed to retrieve user info'}), 500

    logger.info("Stripe webhook processed successfully.")
    return jsonify({'status': 'success'}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, use_reloader=False, host="0.0.0.0", port=port)