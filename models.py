from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, bcrypt

#db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = "user"
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False, unique=True)
    email = db.Column(db.String(150), unique=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default='user')  # ✅ this line
    upload_count = db.Column(db.Integer, default=0)

    def __repr__(self):
        return f'<User {self.username}>'

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)


