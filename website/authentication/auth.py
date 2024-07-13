from flask import Blueprint, render_template, redirect, url_for, request, flash
from .. import db
from ..models import User, UserHistory
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, login_required, logout_user, current_user
from dotenv import load_dotenv
import os

load_dotenv()

auth = Blueprint('auth', __name__, template_folder='templates')

def record_user_history(action):
    # record user history
    history = UserHistory(user_id=current_user.id, action=action)
    db.session.add(history)
    db.session.commit()

@auth.route('/sign_up', methods=['GET', 'POST'])
def sign_up():
    if request.method == 'POST':
        username = request.form.get("username")
        email = request.form.get("email")
        password1 = request.form.get("password1")
        password2 = request.form.get("password2")
    
        email_exists = User.query.filter_by(email=email).first()
        username_exists = User.query.filter_by(username=username).first()
        if email_exists:
            flash('Email is already in use.', category='error')
        elif username_exists:
            flash('Username is already in use.', category='error')
        elif password1 != password2:
            flash('Passwords do not match.', category='error')
        elif len(username) < 2:
            flash('Username is too short.', category='error')
        elif len(password1) < 6:
            flash('Password is too short.', category='error')
        elif len(email) < 4:
            flash('Email is invalid.', category='error')
        else:  # create account
            new_user = User(email=email, username=username, password=generate_password_hash(password1, method='pbkdf2:sha256'))
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user, remember=True)
            flash('Account created!', category='success')

            # record user history
            record_user_history("signed up")

            return redirect(url_for('views.dashboard'))
        
    return render_template('sign_up.html')

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        # goes to admin page if admin
        if email == os.getenv("ADMIN_EMAIL") and password == os.getenv("ADMIN_PASSWORD"):
            return redirect(url_for('admin.admin_page'))

        user = User.query.filter_by(email=email).first()
        if user:
            if check_password_hash(user.password, password):
                flash('Logged in successfully!', category='success')
                login_user(user, remember=True)

                # record user history
                record_user_history("signed in")

                return redirect(url_for('views.landing'))
            else:
                flash('Incorrect password, try again.', category='error')
        else:
            flash('Email does not exist.', category='error')

    return render_template('login.html', user=current_user)

@auth.route('/logout')
@login_required
def logout():
    # record user history
    record_user_history("signed out")  # must use before logout_user()
    logout_user()
    
    return redirect(url_for('views.landing'))
