"""
Admin routes for Smart Text Summarizer
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request, Response, current_app
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from sqlalchemy import func
from models import db, User, Summary, Setting, Notification
from utils import admin_required, paginate_query, generate_csv_report, get_date_range

admin = Blueprint('admin', __name__, url_prefix='/admin')


@admin.route('/dashboard')
@login_required
@admin_required
def dashboard():
    """Admin dashboard with metrics"""
    # Total users
    total_users = User.query.filter_by(role='user').count()
    active_users = User.query.filter_by(role='user', is_active=True).count()
    
    # Total summaries
    total_summaries = Summary.query.filter_by(is_deleted=False).count()
    
    # Today's summaries
    today = datetime.utcnow().date()
    today_start = datetime.combine(today, datetime.min.time())
    today_summaries = Summary.query.filter(
        Summary.created_at >= today_start,
        Summary.is_deleted == False
    ).count()
    
    # Last 7 days activity
    week_ago = datetime.utcnow() - timedelta(days=7)
    weekly_summaries = Summary.query.filter(
        Summary.created_at >= week_ago,
        Summary.is_deleted == False
    ).count()
    
    # Recent activity
    recent_summaries = Summary.query.filter_by(is_deleted=False).order_by(
        Summary.created_at.desc()
    ).limit(10).all()
    
    # New users this week
    new_users = User.query.filter(
        User.created_at >= week_ago,
        User.role == 'user'
    ).count()
    
    # Summary by length
    summary_stats = db.session.query(
        Summary.summary_length,
        func.count(Summary.id)
    ).filter_by(is_deleted=False).group_by(Summary.summary_length).all()
    
    return render_template('admin/dashboard.html',
                         total_users=total_users,
                         active_users=active_users,
                         total_summaries=total_summaries,
                         today_summaries=today_summaries,
                         weekly_summaries=weekly_summaries,
                         new_users=new_users,
                         recent_summaries=recent_summaries,
                         summary_stats=dict(summary_stats))


@admin.route('/users')
@login_required
@admin_required
def users():
    """User management page"""
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config.get('ITEMS_PER_PAGE', 10)
    
    # Filters
    search = request.args.get('search', '').strip()
    status = request.args.get('status', '')
    
    query = User.query.filter_by(role='user')
    
    if search:
        query = query.filter(
            (User.email.ilike(f'%{search}%')) | 
            (User.name.ilike(f'%{search}%'))
        )
    
    if status == 'active':
        query = query.filter_by(is_active=True)
    elif status == 'inactive':
        query = query.filter_by(is_active=False)
    
    query = query.order_by(User.created_at.desc())
    pagination = paginate_query(query, page, per_page)
    
    return render_template('admin/users.html',
                         users=pagination.items,
                         pagination=pagination,
                         search=search,
                         status=status)


@admin.route('/users/<int:id>')
@login_required
@admin_required
def user_detail(id):
    """User detail page"""
    user = User.query.get_or_404(id)
    
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config.get('ITEMS_PER_PAGE', 10)
    
    query = Summary.query.filter_by(user_id=id, is_deleted=False).order_by(Summary.created_at.desc())
    pagination = paginate_query(query, page, per_page)
    
    return render_template('admin/user_detail.html',
                         user=user,
                         summaries=pagination.items,
                         pagination=pagination)


@admin.route('/users/<int:id>/toggle', methods=['POST'])
@login_required
@admin_required
def toggle_user(id):
    """Activate/deactivate user"""
    user = User.query.get_or_404(id)
    
    if user.role == 'admin':
        flash('Cannot modify admin account.', 'danger')
        return redirect(url_for('admin.users'))
    
    user.is_active = not user.is_active
    db.session.commit()
    
    status = 'activated' if user.is_active else 'deactivated'
    flash(f'User {user.email} has been {status}.', 'success')
    return redirect(url_for('admin.users'))


@admin.route('/settings', methods=['GET', 'POST'])
@login_required
@admin_required
def settings():
    """Admin settings page"""
    if request.method == 'POST':
        # Update settings
        Setting.set_value('short_percentage', request.form.get('short_percentage', 20))
        Setting.set_value('medium_percentage', request.form.get('medium_percentage', 40))
        Setting.set_value('long_percentage', request.form.get('long_percentage', 60))
        Setting.set_value('max_input_words', request.form.get('max_input_words', 10000))
        Setting.set_value('summarization_mode', request.form.get('summarization_mode', 'extractive'))
        
        flash('Settings updated successfully.', 'success')
        return redirect(url_for('admin.settings'))
    
    # Get current settings
    current_settings = {
        'short_percentage': Setting.get_value('short_percentage', 20),
        'medium_percentage': Setting.get_value('medium_percentage', 40),
        'long_percentage': Setting.get_value('long_percentage', 60),
        'max_input_words': Setting.get_value('max_input_words', 10000),
        'summarization_mode': Setting.get_value('summarization_mode', 'extractive')
    }
    
    return render_template('admin/settings.html', settings=current_settings)


@admin.route('/reports')
@login_required
@admin_required
def reports():
    """Reports page"""
    return render_template('admin/reports.html')


@admin.route('/reports/download/<report_type>')
@login_required
@admin_required
def download_report(report_type):
    """Generate and download CSV report"""
    period = request.args.get('period', 'monthly')
    start, end = get_date_range(period)
    
    if report_type == 'summaries':
        # Summary counts by date
        data = db.session.query(
            func.date(Summary.created_at),
            func.count(Summary.id)
        ).filter(
            Summary.created_at.between(start, end),
            Summary.is_deleted == False
        ).group_by(func.date(Summary.created_at)).all()
        
        headers = ['Date', 'Summary Count']
        csv_content = generate_csv_report(data, headers)
        filename = f'summary_report_{period}.csv'
        
    elif report_type == 'users':
        # Per-user statistics
        data = db.session.query(
            User.email,
            User.name,
            func.count(Summary.id)
        ).outerjoin(Summary, (Summary.user_id == User.id) & (Summary.is_deleted == False)).filter(
            User.role == 'user'
        ).group_by(User.id).all()
        
        headers = ['Email', 'Name', 'Total Summaries']
        csv_content = generate_csv_report(data, headers)
        filename = f'user_report_{period}.csv'
        
    elif report_type == 'activity':
        # Detailed activity log
        summaries = Summary.query.filter(
            Summary.created_at.between(start, end),
            Summary.is_deleted == False
        ).order_by(Summary.created_at.desc()).all()
        
        data = [
            (s.created_at.strftime('%Y-%m-%d %H:%M'), s.user.email, s.summary_length, s.summary_type, s.input_word_count, s.summary_word_count)
            for s in summaries
        ]
        headers = ['DateTime', 'User Email', 'Length', 'Type', 'Input Words', 'Summary Words']
        csv_content = generate_csv_report(data, headers)
        filename = f'activity_report_{period}.csv'
    else:
        flash('Invalid report type.', 'danger')
        return redirect(url_for('admin.reports'))
    
    return Response(
        csv_content,
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )


@admin.route('/notifications', methods=['GET', 'POST'])
@login_required
@admin_required
def notifications():
    """Notification management page"""
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        message = request.form.get('message', '').strip()
        target = request.form.get('target', 'broadcast')
        user_id = request.form.get('user_id', type=int)
        
        if not title or not message:
            flash('Title and message are required.', 'danger')
            return redirect(url_for('admin.notifications'))
        
        if target == 'broadcast':
            # Broadcast to all users
            notification = Notification(
                user_id=None,
                title=title,
                message=message
            )
            db.session.add(notification)
            flash('Broadcast notification sent to all users.', 'success')
        elif target == 'user' and user_id:
            # Targeted notification
            user = User.query.get(user_id)
            if user:
                notification = Notification(
                    user_id=user_id,
                    title=title,
                    message=message
                )
                db.session.add(notification)
                flash(f'Notification sent to {user.email}.', 'success')
            else:
                flash('User not found.', 'danger')
                return redirect(url_for('admin.notifications'))
        
        db.session.commit()
        return redirect(url_for('admin.notifications'))
    
    # Get all users for targeting
    users = User.query.filter_by(role='user', is_active=True).order_by(User.email).all()
    
    # Recent notifications
    recent_notifications = Notification.query.order_by(Notification.created_at.desc()).limit(20).all()
    
    return render_template('admin/notifications.html',
                         users=users,
                         recent_notifications=recent_notifications)
