"""
Authentication routes for Smart Text Summarizer
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime
from models import db, User, PasswordResetToken
from utils import generate_reset_token, get_reset_token_expiry

auth = Blueprint('auth', __name__)


@auth.route('/login', methods=['GET', 'POST'])
def login():
    """User login page"""
    if current_user.is_authenticated:
        if current_user.is_admin():
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('user.dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember = request.form.get('remember', False)
        
        user = User.query.filter_by(email=email).first()
        
        if user is None or not user.check_password(password):
            flash('Invalid email or password.', 'danger')
            return render_template('auth/login.html')
        
        if not user.is_active:
            flash('Your account has been deactivated. Please contact administrator.', 'danger')
            return render_template('auth/login.html')
        
        # Update last login
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        login_user(user, remember=bool(remember))
        
        next_page = request.args.get('next')
        if next_page:
            return redirect(next_page)
        
        if user.is_admin():
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('user.dashboard'))
    
    return render_template('auth/login.html')


@auth.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Admin login page"""
    if current_user.is_authenticated:
        if current_user.is_admin():
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('user.dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        
        user = User.query.filter_by(email=email, role='admin').first()
        
        if user is None or not user.check_password(password):
            flash('Invalid admin credentials.', 'danger')
            return render_template('auth/admin_login.html')
        
        if not user.is_active:
            flash('Admin account is deactivated.', 'danger')
            return render_template('auth/admin_login.html')
        
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        login_user(user)
        return redirect(url_for('admin.dashboard'))
    
    return render_template('auth/admin_login.html')


@auth.route('/register', methods=['GET', 'POST'])
def register():
    """User registration page"""
    if current_user.is_authenticated:
        return redirect(url_for('user.dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        name = request.form.get('name', '').strip()
        
        # Validation
        errors = []
        
        if not email or '@' not in email:
            errors.append('Please enter a valid email address.')
        
        if len(password) < 6:
            errors.append('Password must be at least 6 characters long.')
        
        if password != confirm_password:
            errors.append('Passwords do not match.')
        
        if not name:
            errors.append('Please enter your name.')
        
        if User.query.filter_by(email=email).first():
            errors.append('Email already registered.')
        
        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('auth/register.html', email=email, name=name)
        
        # Create user
        user = User(email=email, name=name)
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html')


@auth.route('/logout')
@login_required
def logout():
    """Logout user"""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))


@auth.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Request password reset"""
    if current_user.is_authenticated:
        return redirect(url_for('user.dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        user = User.query.filter_by(email=email).first()
        
        if user:
            # Invalidate existing tokens
            PasswordResetToken.query.filter_by(user_id=user.id, is_used=False).update({'is_used': True})
            
            # Create new token
            token = generate_reset_token()
            reset_token = PasswordResetToken(
                user_id=user.id,
                token=token,
                expires_at=get_reset_token_expiry(24)
            )
            db.session.add(reset_token)
            db.session.commit()
            
            # For offline use, show the token directly (no email)
            flash(f'Password reset token generated. Use this link:', 'info')
            reset_url = url_for('auth.reset_password', token=token, _external=True)
            return render_template('auth/forgot_password.html', reset_url=reset_url, token_generated=True)
        else:
            # Don't reveal if email exists
            flash('If the email exists, a reset link has been generated.', 'info')
    
    return render_template('auth/forgot_password.html')


@auth.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Reset password with token"""
    if current_user.is_authenticated:
        return redirect(url_for('user.dashboard'))
    
    reset_token = PasswordResetToken.query.filter_by(token=token).first()
    
    if not reset_token or not reset_token.is_valid():
        flash('Invalid or expired reset token.', 'danger')
        return redirect(url_for('auth.forgot_password'))
    
    if request.method == 'POST':
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'danger')
            return render_template('auth/reset_password.html', token=token)
        
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('auth/reset_password.html', token=token)
        
        # Update password
        user = reset_token.user
        user.set_password(password)
        reset_token.is_used = True
        db.session.commit()
        
        flash('Password reset successful! Please log in.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/reset_password.html', token=token)
