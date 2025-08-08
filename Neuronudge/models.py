# Neuronudge/models.py
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from . import db
from flask_login import UserMixin

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=True)                # full name
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    profile_type = db.Column(db.String(50), nullable=False, default='General')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    tasks = db.relationship('Task', backref='user', lazy=True)
    logs = db.relationship('ActivityLog', backref='user', lazy=True)
    preferences = db.relationship('OnboardingPreferences', back_populates='user', uselist=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.username}>"

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    due_date = db.Column(db.DateTime)
    completed = db.Column(db.Boolean, default=False)
    priority = db.Column(db.Integer, default=3)         # 1 = high, 2 = med, 3 = low
    reminder_set = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f"<Task {self.title}>"

class ActivityLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(255), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f"<ActivityLog {self.action} at {self.timestamp}>"

class OnboardingPreferences(db.Model):
    __tablename__ = 'onboarding_preferences'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True, nullable=False)

    focus_time = db.Column(db.Integer, nullable=False, default=25)
    break_time = db.Column(db.Integer, nullable=False, default=5)
    long_break_time = db.Column(db.Integer, nullable=False, default=15)
    session_goal = db.Column(db.Integer, default=4)
    notifications_enabled = db.Column(db.Boolean, default=True)
    dark_mode_enabled = db.Column(db.Boolean, default=False)

    theme_color = db.Column(db.String(20), default='blue')
    font_size = db.Column(db.String(10), default='medium')
    sound_enabled = db.Column(db.Boolean, default=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship('User', back_populates='preferences')

    def __repr__(self):
        return f"<Preferences User {self.user_id}: Focus {self.focus_time}m / Break {self.break_time}m>"

class PlaceholderModel(db.Model):
    __tablename__ = 'placeholder_model'
    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String(100))
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_on = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Placeholder {self.label}>"
