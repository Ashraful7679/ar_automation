from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class FileHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    input_filename = db.Column(db.String(255))
    output_filename = db.Column(db.String(255)) # Stored relative to static/output
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    def to_dict(self):
        return {
            "id": self.id,
            "input": self.input_filename,
            "output": self.output_filename,
            "date": self.created_at.strftime("%Y-%m-%d %H:%M:%S")
        }
