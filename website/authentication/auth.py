import os
import json
import logging
import boto3
from dotenv import load_dotenv
from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, request, flash, session

# Load environment variables
load_dotenv()

# Read AWS credentials from environment variables
ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID", "")
SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "")
REGION = os.getenv("AWS_REGION", "")

# Log the loaded AWS Region (Do NOT log ACCESS_KEY or SECRET_KEY)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info(f"AWS Region: {REGION}")

# Create the Blueprint
auth = Blueprint('auth', __name__, template_folder='templates')


# Ensure all required environment variables are present
required_env_vars = ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_REGION"]
for var in required_env_vars:
    if not os.getenv(var):
        logger.error(f"Missing required environment variable: {var}")
        raise EnvironmentError(f"Missing required environment variable: {var}")


# Create a Boto3 session and Lambda client
aws_session = boto3.Session(
    aws_access_key_id=ACCESS_KEY,
    aws_secret_access_key=SECRET_KEY,
    region_name=REGION
)
lambda_client = aws_session.client('lambda')

def token_required(f):
    """
    Decorator to ensure the user is logged in and has a valid token.
    It invokes the Lambda function with action "GET_USER" to validate
    the token stored in the session.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = session.get('access_token')
        if not token:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for('auth.login'))

        payload = {
            "action": "GET_USER",
            "token": token
        }

        try:
            response = lambda_client.invoke(
                FunctionName='sb-user-auth-sbUserAuthFunction-zjl3761VSGKj',  # Replace with your actual Lambda function name
                InvocationType='RequestResponse',
                Payload=json.dumps(payload)
            )
            response_payload = json.loads(response['Payload'].read())
            logger.info("Lambda GET_USER response: %s", response_payload)
        except Exception as e:
            logger.error("Error calling Lambda for token validation: %s", e)
            flash("Session expired or invalid. Please log in again.", "warning")
            return redirect(url_for('auth.login'))

        if response_payload.get('statusCode') != 200:
            flash("Session expired or invalid. Please log in again.", "warning")
            return redirect(url_for('auth.login'))

        return f(*args, **kwargs)
    return decorated_function

@auth.route('/sign_up', methods=['GET', 'POST'])
def sign_up():
    """
    Signup endpoint that invokes the Lambda function with action "REGISTER_USER".
    On success, the user is redirected to the login page.
    """
    if request.method == 'POST':
        email = request.form.get("email")
        username = request.form.get("username")
        password1 = request.form.get("password1")
        password2 = request.form.get("password2")

        if password1 != password2:
            flash("Passwords do not match", "error")
            return redirect(url_for('auth.sign_up'))

        payload = {
            "action": "REGISTER_USER",
            "data": {
                "email": email,
                "username": username,
                "password": password1
            }
        }

        try:
            response = lambda_client.invoke(
                FunctionName='sb-user-auth-sbUserAuthFunction-zjl3761VSGKj',  # Replace with your actual Lambda function name
                InvocationType='RequestResponse',
                Payload=json.dumps(payload)
            )
            response_payload = json.loads(response['Payload'].read())
            logger.info("Lambda REGISTER_USER response: %s", response_payload)
        except Exception as e:
            logger.error("Error calling Lambda for sign up: %s", e)
            flash("An error occurred while processing your sign up request.", "error")
            return redirect(url_for('auth.sign_up'))

        if response_payload.get('statusCode') == 201:
            flash("Account created successfully", "success")
            return redirect(url_for('auth.login'))
        else:
            # Attempt to parse an error message from the Lambda response
            body = response_payload.get('body', {})
            if isinstance(body, str):
                try:
                    body = json.loads(body)
                except json.JSONDecodeError:
                    pass
            error_message = body.get("message", "Account creation failed")
            flash(error_message, "error")

    return render_template('sign_up.html')

@auth.route('/login', methods=['GET', 'POST'])
def login():
    """
    Login endpoint that invokes the Lambda function with action "LOGIN_USER".
    On success, an access token is saved in the session.
    """
    if request.method == 'POST':
        username = request.form.get('email')  # Reusing the 'email' field as username
        password = request.form.get('password')

        payload = {
            "action": "LOGIN_USER",
            "data": {
                "username": username,
                "password": password
            }
        }

        try:
            response = lambda_client.invoke(
                FunctionName='sb-user-auth-sbUserAuthFunction-zjl3761VSGKj',  # Replace with your actual Lambda function name
                InvocationType='RequestResponse',
                Payload=json.dumps(payload)
            )
            response_payload = json.loads(response['Payload'].read())
            logger.info("Lambda LOGIN_USER response: %s", response_payload)
        except Exception as e:
            logger.error("Error calling Lambda for login: %s", e)
            flash("An error occurred while processing your login request.", "error")
            return redirect(url_for('auth.login'))

        if response_payload.get('statusCode') == 200:
            # Extract token from the lambda response body
            body_content = response_payload.get('body', {})
            if isinstance(body_content, str):
                try:
                    body_content = json.loads(body_content)
                except json.JSONDecodeError:
                    pass

            token = body_content.get('token')
            if token:
                session['access_token'] = token
                flash("Login successful", "success")
                return redirect(url_for('views.dashboard'))
            else:
                flash("Unexpected response from the server.", "error")
        else:
            # Attempt to parse an error message from the Lambda response
            body = response_payload.get('body', {})
            if isinstance(body, str):
                try:
                    body = json.loads(body)
                except json.JSONDecodeError:
                    pass
            error_message = body.get("message", "Login failed")
            flash(error_message, "error")

    return render_template('login.html')

@auth.route('/logout')
def logout():
    """
    Logout endpoint that removes the access token from the session.
    """
    access_token = session.pop('access_token', None)
    if access_token:
        logger.info("User logged out, token removed: %s", access_token)
    else:
        logger.info("User tried to log out but no token was found in session.")
    flash("You have been logged out.", "info")
    return redirect(url_for('auth.login'))
