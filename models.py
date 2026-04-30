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
    expiry_date = db.Column(db.DateTime, nullable=True)
    
    # Ownership and Limits
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    max_sub_users = db.Column(db.Integer, default=0) # For Admins: how many users they can create
    
    # Quotas
    total_quota = db.Column(db.Integer, default=1000) # Total files allowed
    used_quota = db.Column(db.Integer, default=0)
    daily_quota = db.Column(db.Integer, default=50) # Files per day
    used_today = db.Column(db.Integer, default=0)
    last_reset_date = db.Column(db.Date, default=datetime.now().date)

    # Relationships
    created_users = db.relationship('User', backref=db.backref('creator', remote_side=[id]), lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def reset_daily_quota(self):
        today = datetime.now().date()
        if self.last_reset_date != today:
            self.used_today = 0
            self.last_reset_date = today
            return True
        return False

class FileHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
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
