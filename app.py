from website import create_app
from flask import Flask, request, jsonify, session, redirect, url_for, flash
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

    # Handle the checkout session completed event (grant premium status)
    if event['type'] == 'checkout.session.completed':
        session_data = event['data']['object']
        customer_email = session_data.get('customer_details', {}).get('email')
        logger.info(f"Checkout session completed for {customer_email}.")

        # Call the function to grant premium status using the customer's email
        grant_premium_status_by_email(customer_email)

    # Handle the subscription deleted event (remove premium status)
    elif event['type'] == 'customer.subscription.deleted':
        subscription_data = event['data']['object']
        customer_email = subscription_data.get('customer_email')
        logger.info(f"Subscription canceled for {customer_email}.")

        # Call the function to remove premium status using the customer's email
        remove_premium_status_by_email(customer_email)

    logger.info("Stripe webhook processed successfully.")
    return jsonify({'status': 'success'}), 200

# Function to grant premium status to the user after successful payment
def grant_premium_status_by_email(customer_email):
    logger.info(f"Attempting to grant premium status for {customer_email}.")
    
    # Call the API to grant premium status using the user's email
    grant_premium_url = f"{API_URL}/user/premium/grant_by_email"
    response = requests.put(grant_premium_url, json={'email': customer_email})

    if response.status_code == 200:
        logger.info(f"Premium status successfully granted for {customer_email}.")
    else:
        logger.error(f"Failed to grant premium status for {customer_email}. Response: {response.text}")

# Function to remove premium status when a subscription is canceled
def remove_premium_status_by_email(customer_email):
    logger.info(f"Attempting to remove premium status for {customer_email}.")
    
    # Call the API to remove premium status using the user's email
    remove_premium_url = f"{API_URL}/user/premium/remove_by_email"
    response = requests.put(remove_premium_url, json={'email': customer_email})

    if response.status_code == 200:
        logger.info(f"Premium status successfully removed for {customer_email}.")
    else:
        logger.error(f"Failed to remove premium status for {customer_email}. Response: {response.text}")


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, use_reloader=False, host="0.0.0.0", port=port)
