"""
User routes for Smart Text Summarizer
"""
import os
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, send_file, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from io import BytesIO
from datetime import datetime
from models import db, Summary, Setting, Notification
from summarizer import summarize_text
from utils import user_required, allowed_file, extract_text_from_file, count_words, paginate_query

user = Blueprint('user', __name__)


def get_summarization_settings():
    """Get current summarization settings"""
    return {
        'short_percentage': int(Setting.get_value('short_percentage', 20)),
        'medium_percentage': int(Setting.get_value('medium_percentage', 40)),
        'long_percentage': int(Setting.get_value('long_percentage', 60)),
        'max_input_words': int(Setting.get_value('max_input_words', 10000)),
        'summarization_mode': Setting.get_value('summarization_mode', 'extractive')
    }


@user.route('/dashboard')
@login_required
@user_required
def dashboard():
    """User dashboard"""
    summary_count = current_user.get_summary_count()
    recent_summaries = Summary.query.filter_by(
        user_id=current_user.id, 
        is_deleted=False
    ).order_by(Summary.created_at.desc()).limit(5).all()
    
    unread_notifications = Notification.query.filter(
        (Notification.user_id == current_user.id) | (Notification.user_id == None),
        Notification.is_read == False
    ).count()
    
    return render_template('user/dashboard.html',
                         summary_count=summary_count,
                         recent_summaries=recent_summaries,
                         unread_notifications=unread_notifications)


@user.route('/summarize', methods=['GET', 'POST'])
@login_required
@user_required
def summarize():
    """Text summarization page"""
    settings = get_summarization_settings()
    summary_result = None
    input_text = ''
    custom_percentage = 40  # Default slider value
    
    if request.method == 'POST':
        # Get data from form handling
        input_text = request.form.get('text', '').strip()
        length = request.form.get('length', 'medium')
        mode = request.form.get('mode', settings['summarization_mode'])
        engine = request.form.get('engine', 'nltk') # 'nltk' or 'transformers'
        custom_percentage = request.form.get('custom_percentage', 40, type=int)
        
        if not input_text:
            flash('Please enter some text to summarize.', 'warning')
            return render_template('user/summarizer.html', settings=settings, custom_percentage=custom_percentage)
        
        # Check word limit
        word_count = count_words(input_text)
        if word_count > settings['max_input_words']:
            flash(f'Text exceeds maximum word limit of {settings["max_input_words"]} words.', 'danger')
            return render_template('user/summarizer.html', settings=settings, input_text=input_text, custom_percentage=custom_percentage)
        
        if word_count < 30:
            flash('Please enter at least 30 words for effective summarization.', 'warning')
            return render_template('user/summarizer.html', settings=settings, input_text=input_text, custom_percentage=custom_percentage)
        
        # Generate summary
        try:
            result = summarize_text(input_text, length, mode, settings, custom_percentage if length == 'custom' else None, engine)
            
            # Save to database
            summary = Summary(
                user_id=current_user.id,
                input_text=input_text,
                summary_text=result['summary'],
                summary_length=f"{length} ({result.get('target_percentage', custom_percentage)}%)" if length == 'custom' else length,
                summary_type=result['summary_type'],
                input_word_count=result['input_word_count'],
                summary_word_count=result['summary_word_count']
            )
            db.session.add(summary)
            db.session.commit()
            
            summary_result = {
                **result,
                'id': summary.id
            }
            
        except Exception as e:
            flash(f'Error generating summary: {str(e)}', 'danger')
            return render_template('user/summarizer.html', settings=settings, input_text=input_text, custom_percentage=custom_percentage)
    
    return render_template('user/summarizer.html', 
                         settings=settings, 
                         summary_result=summary_result,
                         input_text=input_text,
                         custom_percentage=custom_percentage)


@user.route('/upload', methods=['POST'])
@login_required
@user_required
def upload_file():
    """Handle file upload"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    allowed_extensions = current_app.config.get('ALLOWED_EXTENSIONS', {'txt', 'pdf', 'docx'})
    
    if not allowed_file(file.filename, allowed_extensions):
        return jsonify({'error': 'File type not allowed. Supported: txt, pdf, docx'}), 400
    
    try:
        # Save file temporarily
        filename = secure_filename(file.filename)
        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
        os.makedirs(upload_folder, exist_ok=True)
        filepath = os.path.join(upload_folder, filename)
        file.save(filepath)
        
        # Extract text
        text = extract_text_from_file(filepath)
        
        # Cleanup temp file
        os.remove(filepath)
        
        if not text.strip():
            return jsonify({'error': 'Could not extract text from file'}), 400
        
        return jsonify({'text': text, 'filename': filename})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@user.route('/history')
@login_required
@user_required
def history():
    """Summary history page"""
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config.get('ITEMS_PER_PAGE', 10)
    
    query = Summary.query.filter_by(
        user_id=current_user.id,
        is_deleted=False
    ).order_by(Summary.created_at.desc())
    
    pagination = paginate_query(query, page, per_page)
    
    return render_template('user/history.html', 
                         summaries=pagination.items,
                         pagination=pagination)


@user.route('/history/<int:id>')
@login_required
@user_required
def view_summary(id):
    """View specific summary"""
    summary = Summary.query.filter_by(
        id=id,
        user_id=current_user.id,
        is_deleted=False
    ).first_or_404()
    
    return render_template('user/view_summary.html', summary=summary)


@user.route('/history/<int:id>/delete', methods=['POST'])
@login_required
@user_required
def delete_summary(id):
    """Delete summary (soft delete)"""
    summary = Summary.query.filter_by(
        id=id,
        user_id=current_user.id,
        is_deleted=False
    ).first_or_404()
    
    summary.is_deleted = True
    db.session.commit()
    
    flash('Summary deleted successfully.', 'success')
    return redirect(url_for('user.history'))


@user.route('/download/<int:id>')
@login_required
@user_required
def download_summary(id):
    """Download summary as text file"""
    summary = Summary.query.filter_by(
        id=id,
        user_id=current_user.id,
        is_deleted=False
    ).first_or_404()
    
    content = f"""SMART TEXT SUMMARIZER
Generated: {summary.created_at.strftime('%Y-%m-%d %H:%M')}
Summary Type: {summary.summary_type.title()}
Summary Length: {summary.summary_length.title()}
Input Words: {summary.input_word_count}
Summary Words: {summary.summary_word_count}

{'='*50}
ORIGINAL TEXT
{'='*50}
{summary.input_text}

{'='*50}
SUMMARY
{'='*50}
{summary.summary_text}
"""
    
    buffer = BytesIO()
    buffer.write(content.encode('utf-8'))
    buffer.seek(0)
    
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f'summary_{summary.id}.txt',
        mimetype='text/plain'
    )


@user.route('/profile', methods=['GET', 'POST'])
@login_required
@user_required
def profile():
    """User profile page"""
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'update_profile':
            name = request.form.get('name', '').strip()
            if name:
                current_user.name = name
                db.session.commit()
                flash('Profile updated successfully.', 'success')
            else:
                flash('Name cannot be empty.', 'danger')
        
        elif action == 'change_password':
            current_password = request.form.get('current_password', '')
            new_password = request.form.get('new_password', '')
            confirm_password = request.form.get('confirm_password', '')
            
            if not current_user.check_password(current_password):
                flash('Current password is incorrect.', 'danger')
            elif len(new_password) < 6:
                flash('New password must be at least 6 characters.', 'danger')
            elif new_password != confirm_password:
                flash('New passwords do not match.', 'danger')
            else:
                current_user.set_password(new_password)
                db.session.commit()
                flash('Password changed successfully.', 'success')
        
        return redirect(url_for('user.profile'))
    
    return render_template('user/profile.html')


@user.route('/notifications')
@login_required
@user_required
def notifications():
    """User notifications page"""
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config.get('ITEMS_PER_PAGE', 10)
    
    query = Notification.query.filter(
        (Notification.user_id == current_user.id) | (Notification.user_id == None)
    ).order_by(Notification.created_at.desc())
    
    pagination = paginate_query(query, page, per_page)
    
    # Mark as read
    for notification in pagination.items:
        if not notification.is_read:
            notification.is_read = True
    db.session.commit()
    
    return render_template('user/notifications.html',
                         notifications=pagination.items,
                         pagination=pagination)
