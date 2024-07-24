from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from flask_login import login_user, login_required, logout_user, current_user
from dotenv import load_dotenv
import os
import requests

load_dotenv()

auth = Blueprint('auth', __name__, template_folder='templates')

API_URL = os.getenv('API_URL', 'http://localhost:5000')  # Use env variable for API URL

def record_user_history(action):
    token = session.get('access_token')
    if token:
        headers = {'Authorization': f'Bearer {token}'}
        data = {'action': action}
        response = requests.post(f"{API_URL}/user_history", json=data, headers=headers)
        if response.status_code != 201:
            flash('Failed to record user history', 'error')

@auth.route('/sign_up', methods=['GET', 'POST'])
def sign_up():
    if request.method == 'POST':
        email = request.form.get("email")
        username = request.form.get("username")
        password1 = request.form.get("password1")
        password2 = request.form.get("password2")

        if password1 != password2:
            flash("Passwords do not match", "error")
            return redirect(url_for('auth.sign_up'))

        data = {
            "email": email,
            "username": username,
            "password": password1
        }

        response = requests.post(f"{API_URL}/register", json=data)
        
        if response.status_code == 201:
            flash("Account created successfully", "success")
            return redirect(url_for('views.dashboard'))
        else:
            flash(response.json().get("message", "Account creation failed"), "error")

    return render_template('sign_up.html')


@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        # goes to admin page if admin
        if email == os.getenv("ADMIN_EMAIL") and password == os.getenv("ADMIN_PASSWORD"):
            return redirect(url_for('admin.admin_page'))

        data = {
            "email": email,
            "password": password
        }

        response = requests.post(f"{API_URL}/login", json=data)
        
        if response.status_code == 200:
            access_token = response.json().get("access_token")
            session['access_token'] = access_token
            record_user_history("signed in")
            return redirect(url_for('views.landing'))
        else:
            flash(response.json().get("message", "Login failed"), "error")

    return render_template('login.html', user=current_user)

@auth.route('/logout')
@login_required
def logout():
    # Record user history
    record_user_history("signed out")
    session.pop('access_token', None)
    return redirect(url_for('views.landing'))
