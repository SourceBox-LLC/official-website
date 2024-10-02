from website import create_app
from flask import Flask, request, jsonify
import os
from dotenv import load_dotenv
import requests
import stripe
import logging

# Load environment variables
load_dotenv()

# Create the Flask app instance
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

    # Handle the event based on its type
    if event['type'] == 'checkout.session.completed':
        handle_checkout_session_completed(event)
    elif event['type'] == 'customer.subscription.updated':
        handle_subscription_updated(event)
    elif event['type'] == 'customer.subscription.deleted':
        handle_subscription_deleted(event)
    elif event['type'] == 'invoice.payment_failed':
        handle_payment_failed(event)
    elif event['type'] == 'invoice.payment_succeeded':
        handle_payment_succeeded(event)
    else:
        logger.info(f"Unhandled event type: {event['type']}")

    logger.info("Stripe webhook processed successfully.")
    return jsonify({'status': 'success'}), 200


def handle_checkout_session_completed(event):
    session_data = event['data']['object']
    customer_id = session_data.get('customer')
    subscription_id = session_data.get('subscription')
    customer_email = session_data.get('customer_details', {}).get('email')
    logger.info(f"Checkout session completed for customer {customer_id} with subscription ID {subscription_id}.")

    if customer_id and subscription_id and customer_email:
        try:
            grant_premium_status_and_store_subscription(customer_id, subscription_id, customer_email)
        except Exception as e:
            logger.error(f"Error granting premium status and storing subscription ID for customer {customer_id}: {e}", exc_info=True)
    else:
        logger.error("Checkout session completed but customer ID, email, or subscription ID is missing.")


def handle_subscription_updated(event):
    subscription = event['data']['object']
    customer_id = subscription.get('customer')
    status = subscription.get('status')
    logger.info(f"Subscription updated for customer {customer_id}, status: {status}.")

    if status == 'active':
        grant_premium_status(customer_id)
    elif status in ['past_due', 'unpaid']:
        logger.warning(f"Payment issues for customer {customer_id}, status: {status}.")
    elif status == 'canceled':
        remove_premium_status(customer_id)


def handle_subscription_deleted(event):
    subscription = event['data']['object']
    customer_id = subscription.get('customer')
    cancel_at_period_end = subscription.get('cancel_at_period_end')

    if cancel_at_period_end:
        logger.info(f"Subscription for customer {customer_id} will cancel at period end.")
    else:
        logger.info(f"Subscription for customer {customer_id} canceled immediately.")
        remove_premium_status(customer_id)


def handle_payment_failed(event):
    invoice = event['data']['object']
    customer_id = invoice.get('customer')
    logger.warning(f"Payment failed for customer {customer_id}.")


def handle_payment_succeeded(event):
    invoice = event['data']['object']
    customer_id = invoice.get('customer')
    logger.info(f"Payment succeeded for customer {customer_id}.")
    grant_premium_status(customer_id)


# Function to grant premium status and store subscription ID in the database
def grant_premium_status_and_store_subscription(customer_id, subscription_id, customer_email):
    logger.info(f"Attempting to grant premium status and store subscription ID for customer {customer_id}.")
    get_user_id_url = f"{API_URL}/users/search"

    try:
        user_response = requests.get(get_user_id_url, params={'stripe_customer_id': customer_id})
        if user_response.status_code == 404:
            user_response = requests.get(get_user_id_url, params={'email': customer_email})

        user_response.raise_for_status()
        user_data = user_response.json()
        user_id = user_data.get('id')

        if not user_id:
            logger.error(f"User with email {customer_email} or customer ID {customer_id} not found.")
            return

        update_customer_id_url = f"{API_URL}/user/{user_id}/stripe/customer"
        update_response = requests.put(update_customer_id_url, json={'stripe_customer_id': customer_id})
        update_response.raise_for_status()
        logger.info(f"Stripe customer ID {customer_id} stored for user ID {user_id}.")

        grant_premium_url = f"{API_URL}/user/{user_id}/premium/grant"
        response = requests.put(grant_premium_url)
        response.raise_for_status()
        logger.info(f"Premium status successfully granted for user ID {user_id}.")

        set_subscription_url = f"{API_URL}/user/{user_id}/stripe/subscription"
        subscription_response = requests.put(set_subscription_url, json={'stripe_subscription_id': subscription_id})
        subscription_response.raise_for_status()
        logger.info(f"Subscription ID {subscription_id} stored for user ID {user_id}.")

    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to grant premium status or store subscription ID for customer {customer_id}: {e}", exc_info=True)


# Function to grant premium status
def grant_premium_status(customer_id):
    logger.info(f"Granting premium status for customer {customer_id}.")
    get_user_id_url = f"{API_URL}/users/search"
    try:
        user_response = requests.get(get_user_id_url, params={'stripe_customer_id': customer_id})
        user_response.raise_for_status()
        user_data = user_response.json()
        user_id = user_data.get('id')

        if not user_id:
            logger.error(f"User with Stripe customer ID {customer_id} not found.")
            return

        grant_premium_url = f"{API_URL}/user/{user_id}/premium/grant"
        response = requests.put(grant_premium_url)
        response.raise_for_status()
        logger.info(f"Premium status successfully granted for user ID {user_id}.")

    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to grant premium status for customer {customer_id}: {e}", exc_info=True)


# Function to remove premium status
def remove_premium_status(customer_id):
    logger.info(f"Removing premium status for customer {customer_id}.")
    get_user_id_url = f"{API_URL}/users/search"
    try:
        user_response = requests.get(get_user_id_url, params={'stripe_customer_id': customer_id})
        user_response.raise_for_status()
        user_data = user_response.json()
        user_id = user_data.get('id')

        if not user_id:
            logger.error(f"User with Stripe customer ID {customer_id} not found.")
            return

        remove_premium_url = f"{API_URL}/user/{user_id}/premium/remove"
        response = requests.put(remove_premium_url)
        response.raise_for_status()
        logger.info(f"Premium status successfully removed for user ID {user_id}.")

    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to remove premium status for customer {customer_id}: {e}", exc_info=True)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, use_reloader=False, host="0.0.0.0", port=port)
