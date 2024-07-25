from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user
from dotenv import load_dotenv
import os
from os import path
import requests

# Load environment variables from .env file
load_dotenv()

# Database
db = SQLAlchemy()
DB_NAME = "database.db"

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI')
    db.init_app(app)

    # Global template like base
    @app.context_processor
    def inject_user():
        return dict(current_user=current_user)

    from website.sourcebox.views import views
    from website.authentication.auth import auth
    from website.admin.admin import admin
    from website.services.services import service

    app.register_blueprint(views, url_prefix='/')
    app.register_blueprint(auth, url_prefix='/')
    app.register_blueprint(admin, url_prefix='/')
    app.register_blueprint(service, url_prefix='/service')

    create_database(app)

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(id):
        api_url = os.getenv('API_URL')
        admin_token = os.getenv('ADMIN_TOKEN')
        response = requests.get(f"{api_url}/users/{id}", headers={'Authorization': f'Bearer {admin_token}'})
        if response.status_code == 200:
            user_data = response.json()
            return User(user_data['id'], user_data['email'], user_data['username'])
        return None

    return app

def create_database(app):
    # This function can be removed or repurposed if not using local DB
    pass

# Mock User class if needed
class User:
    def __init__(self, id, email, username):
        self.id = id
        self.email = email
        self.username = username

    @staticmethod
    def query():
        return None
