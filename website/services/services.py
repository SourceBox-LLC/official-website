from flask import Blueprint, render_template, request, flash, redirect, url_for, abort, send_from_directory
from flask_login import login_required, current_user
from werkzeug.utils import safe_join
import requests
from .. import db
import os

service = Blueprint('service', __name__, template_folder='templates')

API_URL = os.getenv('API_URL')  # Ensure this is set in your .env file

def record_user_history(action):
    token = request.cookies.get('access_token')
    if token:
        headers = {'Authorization': f'Bearer {token}'}
        data = {'action': action}
        response = requests.post(f"{API_URL}/user_history", json=data, headers=headers)
        if response.status_code != 201:
            flash('Failed to record user history', 'error')

@service.route('/service/wikidoc')
@login_required
def wikidoc():
    record_user_history("entered wikidoc")
    return render_template('wikidoc.html')

@service.route('/service/codedoc')
@login_required
def codedoc():
    record_user_history("entered codedoc")
    return render_template('codedoc.html')

@service.route('/service/source-lightning')
@login_required
def source_lightning():
    record_user_history("entered source-lightning")
    return render_template('source_lightning.html')

@service.route('/service/pack-man')
@login_required
def pack_man():
    record_user_history("entered pack-man")
    return render_template('pack_man.html')

@service.route('/service/source-mail')
@login_required
def source_mail():
    record_user_history("entered source-mail")
    return render_template('source_mail.html')
