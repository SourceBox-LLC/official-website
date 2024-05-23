from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user
import os
from os import path


#database
db = SQLAlchemy()
DB_NAME = "database.db"


def create_app():
    application = Flask(__name__)
    application.config['SECRET_KEY'] = "secret"
    application.config['SQLALCHEMY_DATABASE_URI'] ='database-1.c7quggcsmhxr.us-east-2.rds.amazonaws.com' #"sqlite:///{DB_NAME}"
    db.init_app(application)

    #global template like base
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
    

    from .models import User
    #from .models import PlatformUpdates
    create_database(application)

    Login_manager = LoginManager()
    Login_manager.login_view = 'auth.login'
    Login_manager.init_app(application)

    @Login_manager.user_loader
    def load_user(id):
        return User.query.get(int(id))

    return application


def create_database(app):
    if not path.exists('website/' + DB_NAME):
        with app.app_context():
            db.create_all()
        print('Created Database!')