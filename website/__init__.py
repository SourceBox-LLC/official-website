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
    application = Flask(__name__)
    application.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
    application.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI')
    db.init_app(application)

    # Global template like base
    @application.context_processor
    def inject_user():
        return dict(current_user=current_user)

    from website.sourcebox.views import views
    from website.authentication.auth import auth
    from website.admin.admin import admin
    from website.services.services import service

    application.register_blueprint(views, url_prefix='/')
    application.register_blueprint(auth, url_prefix='/')
    application.register_blueprint(admin, url_prefix='/')
    application.register_blueprint(service, url_prefix='/service')

    create_database(application)

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(application)

    @login_manager.user_loader
    def load_user(id):
        api_url = os.getenv('API_URL')
        admin_token = os.getenv('ADMIN_TOKEN')
        response = requests.get(f"{api_url}/users/{id}", headers={'Authorization': f'Bearer {admin_token}'})
        if response.status_code == 200:
            user_data = response.json()
            return User(user_data['id'], user_data['email'], user_data['username'])
        return None

    return application

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
