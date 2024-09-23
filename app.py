from website import create_app
from flask import Flask, request, jsonify, session, url_for, redirect, flash
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

# Ensure the secret key is set for session management
app.secret_key = os.getenv('SECRET_KEY', 'your_default_secret_key')
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = True

# Helper function to get headers with the JWT token
def get_headers():
    token = session.get('access_token')
    if token:
        logger.debug(f"Token found in session: {token[:10]}... (truncated for security)")
        return {'Authorization': f'Bearer {token}'}
    else:
        logger.debug("No token found in session.")
        return {}

# Route to create the Stripe Checkout session
@app.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    logger.info("create_checkout_session route accessed.")
    # Ensure the user is logged in
    if 'access_token' not in session:
        flash('You need to log in to proceed with the payment.', 'error')
        return redirect(url_for('login_page'))

    try:
        # Include the success_url with a query parameter
        success_url = url_for('payment_success', _external=True, _scheme='https') + '?session_id={CHECKOUT_SESSION_ID}'
        cancel_url = url_for('payment_cancel', _external=True, _scheme='https')
        logger.info(f"Constructed success_url: {success_url}")
        logger.info(f"Constructed cancel_url: {cancel_url}")

        # Define your line items and other session parameters
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[
                {
                    'price': 'price_1Q1YDjRsIPLRGXtLO9abyGvz',  # Replace with your actual Price ID
                    'quantity': 1,
                },
            ],
            mode='payment',
            success_url=success_url,
            cancel_url=cancel_url,
        )
        logger.info(f"Stripe Checkout session created: {checkout_session.id}")
        return jsonify({'id': checkout_session.id})
    except Exception as e:
        logger.error(f"Error creating Stripe Checkout session: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


# Route to handle payment success
@app.route('/payment_success')
def payment_success():
    logger.info("Payment success route accessed.")
    session_id = request.args.get('session_id')

    if not session_id:
        flash('Payment session ID is missing.', 'error')
        return redirect(url_for('dashboard'))

    try:
        # Fetch the session data from Stripe to get the customer's email
        session_data = stripe.checkout.Session.retrieve(session_id)
        customer_email = session_data.get('customer_details', {}).get('email')

        if not customer_email:
            flash('Could not retrieve customer email.', 'error')
            return redirect(url_for('dashboard'))

        # Log the emails being compared
        user_email = session.get('email')
        logger.info(f"Comparing emails: customer_email={customer_email}, user_email={user_email}")

        # Normalize and compare emails
        if customer_email.strip().lower() != user_email.strip().lower():
            flash('Email mismatch. Please contact support.', 'error')
            logger.error(f"Email mismatch: customer_email={customer_email}, user_email={user_email}")
            return redirect(url_for('dashboard'))

        # Call the update_premium_status function
        return update_premium_status()
    except Exception as e:
        logger.error(f"Error in payment_success: {e}", exc_info=True)
        flash('Error retrieving payment information. Please contact support.', 'error')
        return redirect(url_for('dashboard'))

# Route to handle payment cancellation
@app.route('/payment_cancel')
def payment_cancel():
    flash('Payment was cancelled.', 'info')
    return redirect(url_for('dashboard'))

def update_premium_status():
    logging.info("update_premium_status called.")
    try:
        # Use the existing access token stored in session
        headers = get_headers()
        if not headers:
            logging.error("No access token available in session.")
            flash('You need to be logged in to update premium status.', 'error')
            return redirect(url_for('login_page'))

        # Get the user ID from the API
        user_id_url = f"{API_URL}/user/id"
        response = requests.get(user_id_url, headers=headers)
        logging.info(f"User ID response: {response.status_code}, {response.text}")

        if response.status_code == 200:
            user_id = response.json().get('user_id')
            logging.info(f"User ID obtained: {user_id}")

            if not user_id:
                logging.error("User ID not found in response.")
                flash('Failed to retrieve user ID. Please contact support.', 'error')
                return redirect(url_for('dashboard'))

            # Make a request to the API to grant premium status
            user_update_url = f"{API_URL}/user/{user_id}/premium/grant"
            grant_response = requests.put(user_update_url, headers=headers)
            logging.info(f"Grant premium status response: {grant_response.status_code}, {grant_response.text}")

            if grant_response.status_code == 200:
                logging.info(f"Premium status successfully granted for user ID {user_id}.")
                flash('Your premium status has been activated!', 'success')
                return redirect(url_for('dashboard'))
            else:
                logging.error(f"Failed to grant premium status for user ID {user_id}. Response: {grant_response.text}")
                flash('Failed to activate premium status. Please contact support.', 'error')
                return redirect(url_for('dashboard'))
        else:
            logging.error(f"Failed to retrieve user ID. Response: {response.text}")
            flash('Failed to retrieve user information. Please contact support.', 'error')
            return redirect(url_for('dashboard'))

    except Exception as e:
        logging.error(f"Error in update_premium_status: {e}", exc_info=True)
        flash('An error occurred while updating your premium status. Please contact support.', 'error')
        return redirect(url_for('dashboard'))

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
        logging.error("Invalid payload from Stripe.", exc_info=True)
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError as e:
        logging.error("Invalid signature verification from Stripe.", exc_info=True)
        return jsonify({'error': 'Invalid signature'}), 400

    # Handle the checkout session completed event
    if event['type'] == 'checkout.session.completed':
        session_data = event['data']['object']
        customer_email = session_data.get('customer_details', {}).get('email')
        logging.info(f"Checkout session completed for {customer_email}.")

        # You can perform additional server-side processing here if needed

    logging.info("Stripe webhook processed successfully.")
    return jsonify({'status': 'success'}), 200

# Ensure the user's email is stored in the session upon login
@app.route('/login', methods=['POST'])
def login():
    email = request.form.get('email')
    password = request.form.get('password')

    logger.info(f"Login attempt for email: {email}")

    try:
        # Make a request to your authentication API
        response = requests.post(f"{API_URL}/login", json={'email': email, 'password': password})
        logger.info(f"Authentication API response: {response.status_code}, {response.text}")

        if response.status_code == 200:
            data = response.json()
            access_token = data.get('access_token')
            user_email = data.get('email')

            session['access_token'] = access_token
            session['email'] = user_email  # Store email in session

            flash('Logged in successfully!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password.', 'error')
            return redirect(url_for('login_page'))
    except Exception as e:
        logging.error(f"Error during login: {e}", exc_info=True)
        flash('An error occurred during login. Please try again later.', 'error')
        return redirect(url_for('login_page'))

# Dashboard route
@app.route('/dashboard')
def dashboard():
    # Your code to render the dashboard
    logger.info("Dashboard accessed.")
    return "Welcome to your dashboard!"

# Login page route
@app.route('/login')
def login_page():
    # Your code to render the login page
    logger.info("Login page accessed.")
    return "Login page"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, use_reloader=False, host="0.0.0.0", port=port)
