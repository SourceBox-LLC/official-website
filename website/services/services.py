from flask import Blueprint, render_template, request, flash, redirect, url_for, abort, session
from flask_login import login_required, current_user
from werkzeug.utils import safe_join
from functools import wraps
import requests
from .. import db
import os
import logging
import json
import boto3

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize AWS clients
aws_session = boto3.Session(
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_REGION")
)
lambda_client = aws_session.client('lambda')

service = Blueprint('service', __name__, template_folder='templates')

API_URL = os.getenv('API_URL')  # Ensure this is set in your .env file

def token_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = session.get('access_token')
        logger.info(f"Checking token: {token}")
        if not token:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for('auth.login'))
        
        payload = {
            "action": "GET_USER",
            "token": token
        }

        try:
            response = lambda_client.invoke(
                FunctionName='sb-user-auth-sbUserAuthFunction-3StRr85VyfEC',
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

@service.route('/deepquery')
@token_required
def deepquery():
    token = session.get('access_token')
    if not token:
        flash("Please log in to access this page.", "warning")
        return redirect(url_for('auth.login'))
    
    headers = {'Authorization': f'Bearer {token}'}
    
    payload = {
        "action": "GET_USER",
        "token": token
    }

    try:
        response = lambda_client.invoke(
            FunctionName='sb-user-auth-sbUserAuthFunction-3StRr85VyfEC',
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
        response_payload = json.loads(response['Payload'].read())
    except Exception as e:
        logger.error("Error calling Lambda for token validation: %s", e)
        flash("Session expired or invalid. Please log in again.", "warning")
        return redirect(url_for('auth.login'))

    if response_payload.get('statusCode') != 200:
        flash("Session expired or invalid. Please log in again.", "warning")
        return redirect(url_for('auth.login'))
        
    return redirect("https://deepquery.streamlit.app")

@service.route('/service/source-lightning')
@token_required
def source_lightning():
    return redirect("https://sourcebox-sourcelightning-8952e6a21707.herokuapp.com")

@service.route('/pack-man')
@token_required
def pack_man():
    token = session.get('access_token')
    if not token:
        flash("Please log in to access this page.", "warning")
        return redirect(url_for('auth.login'))
    
    headers = {'Authorization': f'Bearer {token}'}
    
    payload = {
        "action": "GET_USER",
        "token": token
    }

    try:
        response = lambda_client.invoke(
            FunctionName='sb-user-auth-sbUserAuthFunction-3StRr85VyfEC',
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
        response_payload = json.loads(response['Payload'].read())
    except Exception as e:
        logger.error("Error calling Lambda for token validation: %s", e)
        flash("Session expired or invalid. Please log in again.", "warning")
        return redirect(url_for('auth.login'))

    if response_payload.get('statusCode') != 200:
        flash("Session expired or invalid. Please log in again.", "warning")
        return redirect(url_for('auth.login'))
        
    return redirect("https://packman.streamlit.app")



