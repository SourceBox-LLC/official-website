from . import db
from flask_login import UserMixin
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from datetime import datetime


#User data model
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True)
    username = db.Column(db.String(150), unique=True)
    password = db.Column(db.String(150))
    date_created = db.Column(db.DateTime(timezone=True), default=func.now())
    premium_status = db.Column(db.Boolean, default=False)
    history = relationship('UserHistory', backref='user', lazy=True)



class UserHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    action = db.Column(db.String(150))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    #formating output
    def __repr__(self):
        return f'<UserHistory {self.user_id} {self.action}>'



# admin update tool for updates.html
class PlatformUpdates(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title =  db.Column(db.String(150), unique=True)
    content = db.Column(db.String(150), unique=True)
    
   