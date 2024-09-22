from website import create_app
from flask import Flask, request, jsonify, session
import os
from dotenv import load_dotenv
import requests
import stripe
# bug report google form link https://forms.gle/sA1Z1FRESpwFo6CJA

load_dotenv()

app = create_app()

stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
API_URL = os.getenv('API_URL')


# webhook endpoint for handling Stripe events
# Your webhook endpoint for handling Stripe events
@app.route('/stripe/webhook', methods=['POST'])
def stripe_webhook():
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')

    endpoint_secret = os.getenv('STRIPE_WEBHOOK_SECRET')
    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError as e:
        # Invalid payload
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        return jsonify({'error': 'Invalid signature'}), 400

    # Handle the event type
    if event['type'] == 'checkout.session.completed':
        session_data = event['data']['object']
        customer_email = session_data['customer_details']['email']

        # Fetch the user ID using the correct method (GET)
        headers = {'Authorization': f'Bearer {session.get("access_token")}'}
        user_search_url = f"{API_URL}/users/search"
        
        # Use GET request with query parameters to search by email
        response = requests.get(user_search_url, params={'email': customer_email}, headers=headers)

        if response.status_code == 200:
            user_data = response.json()
            user_id = user_data.get('id')
            if user_id:
                # Grant premium status using the correct endpoint
                user_update_url = f"{API_URL}/user/{user_id}/premium/grant"
                grant_response = requests.put(user_update_url, headers=headers)

                if grant_response.status_code == 200:
                    print(f"Premium status granted for user ID {user_id}")
                else:
                    print(f"Failed to grant premium status: {grant_response.text}")
            else:
                print(f"User with email {customer_email} not found.")
        else:
            print(f"Failed to retrieve user ID for {customer_email}: {response.text}")

    return jsonify({'status': 'success'}), 200




if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, use_reloader=False, host="0.0.0.0", port=port)