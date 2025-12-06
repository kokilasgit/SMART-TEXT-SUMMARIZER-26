"""
Smart Text Summarizer - Main Flask Application
A comprehensive text summarization system with user and admin modules
"""
import sys
import os

# Add Backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'Backend'))

from flask import Flask, redirect, url_for
from flask_login import LoginManager

from config import Config
from models import db, User, Setting

# Create Flask app
app = Flask(__name__, 
            template_folder='frontend/templates',
            static_folder='frontend/static')

app.config.from_object(Config)

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'warning'


@login_manager.user_loader
def load_user(user_id):
    """Load user by ID for Flask-Login"""
    return User.query.get(int(user_id))


def create_default_admin():
    """Create default admin user if not exists"""
    admin = User.query.filter_by(email=Config.DEFAULT_ADMIN_EMAIL).first()
    if not admin:
        admin = User(
            email=Config.DEFAULT_ADMIN_EMAIL,
            name=Config.DEFAULT_ADMIN_NAME,
            role='admin'
        )
        admin.set_password(Config.DEFAULT_ADMIN_PASSWORD)
        db.session.add(admin)
        db.session.commit()
        print(f"[INFO] Default admin created: {Config.DEFAULT_ADMIN_EMAIL}")


def create_default_settings():
    """Create default settings if not exists"""
    for key, value in Config.DEFAULT_SETTINGS.items():
        if not Setting.query.filter_by(key=key).first():
            setting = Setting(key=key, value=str(value))
            db.session.add(setting)
    db.session.commit()


def init_database():
    """Initialize database and create defaults"""
    with app.app_context():
        # Create all tables
        db.create_all()
        
        # Create defaults
        create_default_admin()
        create_default_settings()
        
        # Ensure upload folder exists
        os.makedirs(app.config.get('UPLOAD_FOLDER', 'uploads'), exist_ok=True)


# Register blueprints
from auth import auth
from user_routes import user
from admin_routes import admin

app.register_blueprint(auth)
app.register_blueprint(user)
app.register_blueprint(admin)


# Root route
@app.route('/')
def index():
    """Redirect to login page"""
    return redirect(url_for('auth.login'))


# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return redirect(url_for('auth.login'))


@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return redirect(url_for('auth.login'))


# Template context processors
@app.context_processor
def utility_processor():
    """Add utility functions to templates"""
    from datetime import datetime
    return {
        'now': datetime.utcnow(),
        'format_date': lambda d: d.strftime('%Y-%m-%d') if d else 'N/A',
        'format_datetime': lambda d: d.strftime('%Y-%m-%d %H:%M') if d else 'N/A'
    }


if __name__ == '__main__':
    # Initialize database
    init_database()
    
    print("\n" + "="*60)
    print("   SMART TEXT SUMMARIZER")
    print("="*60)
    print(f"   Admin Login: {Config.DEFAULT_ADMIN_EMAIL}")
    print(f"   Admin Password: {Config.DEFAULT_ADMIN_PASSWORD}")
    print("="*60)
    print("   Open http://127.0.0.1:5000 in your browser")
    print("="*60 + "\n")
    
    # Run the app
    # host='0.0.0.0' allows access from other devices on the network
    # debug=True enables auto-reload on code changes (disable in production)
    app.run(debug=True, host='0.0.0.0', port=5000)