"""
Utility functions for Smart Text Summarizer
"""
import os
import secrets
import csv
from io import StringIO, BytesIO
from datetime import datetime, timedelta
from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user


def generate_reset_token():
    """Generate a secure password reset token"""
    return secrets.token_urlsafe(32)


def get_reset_token_expiry(hours=24):
    """Get expiry datetime for reset token"""
    return datetime.utcnow() + timedelta(hours=hours)


def allowed_file(filename, allowed_extensions):
    """Check if file has allowed extension"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions


def extract_text_from_file(file_path):
    """Extract text content from uploaded file"""
    ext = file_path.rsplit('.', 1)[1].lower()
    
    if ext == 'txt':
        return extract_from_txt(file_path)
    elif ext == 'pdf':
        return extract_from_pdf(file_path)
    elif ext == 'docx':
        return extract_from_docx(file_path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")


def extract_from_txt(file_path):
    """Extract text from TXT file"""
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        return f.read()


def extract_from_pdf(file_path):
    """Extract text from PDF file"""
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text
    except ImportError:
        raise ImportError("PyPDF2 is required for PDF support. Install with: pip install PyPDF2")
    except Exception as e:
        raise ValueError(f"Error reading PDF: {str(e)}")


def extract_from_docx(file_path):
    """Extract text from DOCX file"""
    try:
        from docx import Document
        doc = Document(file_path)
        text = "\n".join([para.text for para in doc.paragraphs])
        return text
    except ImportError:
        raise ImportError("python-docx is required for DOCX support. Install with: pip install python-docx")
    except Exception as e:
        raise ValueError(f"Error reading DOCX: {str(e)}")


def count_words(text):
    """Count words in text"""
    return len(text.split())


def admin_required(f):
    """Decorator to require admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.admin_login'))
        if not current_user.is_admin():
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('user.dashboard'))
        return f(*args, **kwargs)
    return decorated_function


def user_required(f):
    """Decorator to require authenticated user"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        if not current_user.is_active:
            flash('Your account has been deactivated.', 'danger')
            return redirect(url_for('auth.logout'))
        return f(*args, **kwargs)
    return decorated_function


def generate_csv_report(data, headers):
    """Generate CSV from data"""
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    for row in data:
        writer.writerow(row)
    return output.getvalue()


def format_datetime(dt):
    """Format datetime for display"""
    if dt is None:
        return 'Never'
    return dt.strftime('%Y-%m-%d %H:%M')


def paginate_query(query, page, per_page):
    """Paginate a SQLAlchemy query"""
    return query.paginate(page=page, per_page=per_page, error_out=False)


def get_date_range(period='daily'):
    """Get date range for reports"""
    today = datetime.utcnow().date()
    
    if period == 'daily':
        start = datetime.combine(today, datetime.min.time())
        end = datetime.combine(today, datetime.max.time())
    elif period == 'weekly':
        start = datetime.combine(today - timedelta(days=today.weekday()), datetime.min.time())
        end = datetime.combine(today, datetime.max.time())
    elif period == 'monthly':
        start = datetime.combine(today.replace(day=1), datetime.min.time())
        end = datetime.combine(today, datetime.max.time())
    else:
        start = datetime.combine(today - timedelta(days=30), datetime.min.time())
        end = datetime.combine(today, datetime.max.time())
    
    return start, end
