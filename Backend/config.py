"""
Configuration settings for Smart Text Summarizer
"""
import os

# Base directory
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    """Application configuration"""
    
    # Secret key for session management
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'smart-text-summarizer-secret-key-2024'
    
    # Database - SQLite for offline operation
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(BASE_DIR, 'database.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Upload settings
    UPLOAD_FOLDER = os.path.join(BASE_DIR, '..', 'documents')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx'}
    
    # Summarization defaults
    DEFAULT_SETTINGS = {
        'short_percentage': 20,
        'medium_percentage': 40,
        'long_percentage': 60,
        'max_input_words': 10000,
        'summarization_mode': 'both'  # extractive, abstractive, or both
    }
    
    # Admin credentials (created on first run)
    DEFAULT_ADMIN_EMAIL = 'admin@admin.com'
    DEFAULT_ADMIN_PASSWORD = 'admin123'
    DEFAULT_ADMIN_NAME = 'Administrator'
    
    # Pagination
    ITEMS_PER_PAGE = 10
    
    # Password reset token expiry (in hours)
    RESET_TOKEN_EXPIRY = 24
