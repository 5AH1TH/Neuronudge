# Neuronudge/__init__.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
import os

# --- Initialize extensions ---
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()  # keep lowercase

# Flask-Login configuration defaults
login_manager.login_view = 'auth.login'  # route name for login page
login_manager.login_message_category = 'info'  # flash message category

def create_app():
    """
    Flask application factory function.
    """
    app = Flask(__name__)

    # --- Configuration ---
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'dev' #Replace later
    app.config['ALLOWED_EXTENSIONS'] = {"png","jpg","jpeg","gif"}
    app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads', 'avatars')
    app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024
    
    # --- Initialize extensions with app ---
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    # --- Import models to register with SQLAlchemy ---
    from Neuronudge import models  # ensures models are registered

    # --- Flask-Login user loader ---
    @login_manager.user_loader
    def load_user(user_id):
        from Neuronudge.models import User  # local import to avoid circular import
        return User.query.get(int(user_id))

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # --- Register Blueprints ---
    from Neuronudge.views import main
    from Neuronudge.auth import auth
    
    # import blueprints
    app.register_blueprint(main)
    app.register_blueprint(auth, url_prefix='/auth')

    # --- Auto-create database tables if they don't exist ---
    with app.app_context():
        db.create_all()


    @app.after_request
    def add_header(response):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response
    
    return app
