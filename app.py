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
        logger.info(f"Stripe event type: {event['type']} constructed successfully.")
    except ValueError as e:
        logger.error("Invalid payload from Stripe.", exc_info=True)
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError as e:
        logger.error("Invalid signature verification from Stripe.", exc_info=True)
        return jsonify({'error': 'Invalid signature'}), 400
    except Exception as e:
        logger.error("Unexpected error while processing webhook.", exc_info=True)
        return jsonify({'error': 'Unexpected error'}), 500

    # Handle the checkout session completed event (grant premium status and store subscription ID)
    if event['type'] == 'checkout.session.completed':
        session_data = event['data']['object']
        customer_email = session_data.get('customer_details', {}).get('email')
        subscription_id = session_data.get('subscription')

        logger.info(f"Checkout session completed for {customer_email} with subscription ID {subscription_id}.")

        if customer_email and subscription_id:
            try:
                grant_premium_status_and_store_subscription(customer_email, subscription_id)
            except Exception as e:
                logger.error(f"Error granting premium status and storing subscription ID for {customer_email}: {e}", exc_info=True)
        else:
            logger.error("Checkout session completed but missing customer email or subscription ID.")

    # Handle the subscription deleted event (remove premium status and clear subscription ID)
    elif event['type'] == 'customer.subscription.deleted':
        subscription_data = event['data']['object']
        customer_email = subscription_data.get('customer_email')
        logger.info(f"Subscription canceled for {customer_email}.")

        if customer_email:
            try:
                remove_premium_status_and_clear_subscription(customer_email)
            except Exception as e:
                logger.error(f"Error removing premium status and clearing subscription ID for {customer_email}: {e}", exc_info=True)
        else:
            logger.error("Subscription canceled but customer email is missing.")
    
    logger.info("Stripe webhook processed successfully.")
    return jsonify({'status': 'success'}), 200


# Function to grant premium status and store the subscription ID
def grant_premium_status_and_store_subscription(customer_email, subscription_id):
    logger.info(f"Granting premium status and storing subscription ID for {customer_email}.")

    # Call the API to grant premium status and store subscription ID using the user's email
    grant_premium_url = f"{API_URL}/user/premium/grant_by_email"
    subscription_url = f"{API_URL}/user/stripe/subscription"

    try:
        # Grant premium status
        response = requests.put(grant_premium_url, json={'email': customer_email})
        response.raise_for_status()
        logger.info(f"Premium status successfully granted for {customer_email}.")

        # Store subscription ID
        response = requests.put(subscription_url, json={'email': customer_email, 'stripe_subscription_id': subscription_id})
        response.raise_for_status()
        logger.info(f"Subscription ID {subscription_id} successfully stored for {customer_email}.")
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to grant premium status or store subscription ID for {customer_email}: {e}", exc_info=True)

# Function to remove premium status and clear the subscription ID
def remove_premium_status_and_clear_subscription(customer_email):
    logger.info(f"Removing premium status and clearing subscription ID for {customer_email}.")

    # Call the API to remove premium status and clear subscription ID using the user's email
    remove_premium_url = f"{API_URL}/user/premium/remove_by_email"
    clear_subscription_url = f"{API_URL}/user/stripe/cancel_subscription"

    try:
        # Remove premium status
        response = requests.put(remove_premium_url, json={'email': customer_email})
        response.raise_for_status()
        logger.info(f"Premium status successfully removed for {customer_email}.")

        # Clear subscription ID
        response = requests.put(clear_subscription_url, json={'email': customer_email})
        response.raise_for_status()
        logger.info(f"Subscription ID cleared for {customer_email}.")
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to remove premium status or clear subscription ID for {customer_email}: {e}", exc_info=True)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, use_reloader=False, host="0.0.0.0", port=port)
