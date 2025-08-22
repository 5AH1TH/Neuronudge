from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, abort
from flask_login import login_required, current_user
from .models import Task, OnboardingPreferences, User
from . import db
from .forms import OnboardingForm, TaskForm, ProfileUpdateForm, PasswordChangeForm, RegisterForm
from datetime import datetime
from werkzeug.security import check_password_hash, generate_password_hash
import logging
import pytz
from datetime import timedelta

views = Blueprint('views', __name__)

priority_map = {
    'high': 1,
    'medium': 2,
    'low': 3
}

reverse_priority_map = {v: k for k, v in priority_map.items()}

# Set up a logger for audit trail (simple console logging here)
logger = logging.getLogger('neuronudge.audit')
if not logger.hasHandlers():
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

def log_action(user_id, action):
    logger.info(f'User {user_id} performed action: {action}')

@views.route('/dashboard')
@login_required
def dashboard():
    page = request.args.get('page', 1, type=int)
    per_page = 10

    filter_status = request.args.get('status', 'all')
    filter_priority = request.args.get('priority', 'all')
    search_term = request.args.get('search', '').strip()

    # Base query for all tasks owned by the current user
    base_query = Task.query.filter_by(user_id=current_user.id)

    if filter_status == 'completed':
        base_query = base_query.filter_by(completed=True)
    elif filter_status == 'pending':
        base_query = base_query.filter_by(completed=False)

    if filter_priority in ['1', '2', '3']:
        base_query = base_query.filter_by(priority=int(filter_priority))

    if search_term:
        base_query = base_query.filter(Task.title.ilike(f'%{search_term}%'))

    tasks = base_query.all()

    paginated_tasks = base_query.order_by(
        Task.priority.asc(),
        Task.due_date.asc().nulls_last()
    ).paginate(page=page, per_page=per_page)

    total_tasks = Task.query.filter_by(user_id=current_user.id).count()
    pending_tasks = Task.query.filter_by(user_id=current_user.id, completed=False).count()
    completed_tasks = Task.query.filter_by(user_id=current_user.id, completed=True).count()
    overdue_tasks = Task.query.filter(
        Task.user_id == current_user.id,
        Task.completed == False,
        Task.due_date != None,
        Task.due_date < datetime.utcnow()
    ).count()

    task_counts = {
        'total': total_tasks,
        'pending': pending_tasks,
        'completed': completed_tasks,
        'overdue': overdue_tasks
    }

    recent_tasks = Task.query.filter_by(user_id=current_user.id).order_by(
        Task.priority.asc(),
        Task.due_date.asc().nulls_last()
    ).limit(10).all()

    onboarding = OnboardingPreferences.query.filter_by(user_id=current_user.id).first()

    return render_template(
        'dashboard.html',
        tasks=tasks,   # 👈 now available in template
        recent_tasks=recent_tasks,
        onboarding=onboarding,
        filter_status=filter_status,
        filter_priority=filter_priority,
        search_term=search_term,
        task_counts=task_counts,
        paginated_tasks=paginated_tasks
    )

@views.route('/onboarding', methods=['GET', 'POST'])
@login_required
def onboarding():
    form = OnboardingForm()
    existing = OnboardingPreferences.query.filter_by(user_id=current_user.id).first()
    
    if form.validate_on_submit():
        if existing:
            existing.focus_time = form.focus_time.data
            existing.break_time = form.break_time.data
            existing.notifications_enabled = form.notifications_enabled.data
        else:
            new_pref = OnboardingPreferences(
                focus_time=form.focus_time.data,
                break_time=form.break_time.data,
                notifications_enabled=form.notifications_enabled.data,
                user_id=current_user.id
            )
            db.session.add(new_pref)
        db.session.commit()
        flash("Preferences saved!", category='success')
        log_action(current_user.id, "Updated onboarding preferences")
        return redirect(url_for('views.dashboard'))
    
    if existing:
        form.focus_time.data = existing.focus_time
        form.break_time.data = existing.break_time
        form.notifications_enabled.data = existing.notifications_enabled

    return render_template('onboarding.html', form=form)

@views.route('/task/new', methods=['GET', 'POST'])
@login_required
def create_task():
    form = TaskForm()
    if form.validate_on_submit():
        prefs = OnboardingPreferences.query.filter_by(user_id=current_user.id).first()

        computed_due = None
        if form.due_date.data:
            computed_due = datetime.combine(
                form.due_date.data - timedelta(days=1),
                datetime.strptime("11:59", "%H:%M").time()
            )
        else:
            if prefs:
                try:
                    tz = pytz.timezone(prefs.timezone or 'UTC')
                except Exception:
                    tz = pytz.timezone('UTC')
                now_utc = datetime.utcnow().replace(tzinfo=pytz.UTC)
                now_local = now_utc.astimezone(tz)
                local_due = now_local + timedelta(minutes=int(prefs.focus_time or 25))
                computed_due = local_due.astimezone(pytz.UTC).replace(tzinfo=None)

        # ✅ store priority as int, completed from status
        new_task = Task(
            title=form.title.data,
            description=form.description.data,
            completed=(form.status.data == "completed"),
            due_date=computed_due,
            priority=int(form.priority.data),   # force integer
            reminder_set=form.reminder_set.data,
            user_id=current_user.id
        )

        db.session.add(new_task)
        db.session.commit()

        flash("Task added successfully!", category='success')
        log_action(current_user.id, f"Created task: {new_task.title}")
        return redirect(url_for('views.dashboard'))

    return render_template('create_task.html', form=form)



@views.route('/task/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_task(id):
    task = Task.query.get_or_404(id)
    if task.user_id != current_user.id:
        flash("Unauthorized access.", category='error')
        abort(403)

    form = TaskForm(obj=task)

    if request.method == 'GET':
        form.priority.data = str(task.priority)   # preload as string for SelectField
        form.status.data = "completed" if task.completed else "not_started"

    if form.validate_on_submit():
        old_title = task.title
        task.title = form.title.data
        task.description = form.description.data
        task.completed = (form.status.data == "completed")

        if form.due_date.data:
            task.due_date = datetime.combine(
                form.due_date.data - timedelta(days=1),
                datetime.strptime("11:59", "%H:%M").time()
            )

        # ✅ store priority as int
        task.priority = int(form.priority.data)
        task.reminder_set = form.reminder_set.data

        db.session.commit()

        flash("Task updated successfully!", category='success')
        log_action(current_user.id, f"Edited task from '{old_title}' to '{task.title}'")
        return redirect(url_for('views.dashboard'))

    return render_template('edit_task.html', form=form, task=task)



@views.route('/task/delete/<int:id>', methods=['POST'])
@login_required
def delete_task(id):
    task = Task.query.get_or_404(id)

    # make sure user owns the task
    if task.user_id != current_user.id:
        flash("Unauthorized access.", category='error')
        abort(403)

    try:
        db.session.delete(task)
        db.session.commit()
        flash("Task deleted successfully!", category='success')
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting task: {str(e)}", category='error')

    return redirect(url_for('views.dashboard'))


@views.route('/tasks/export')
@login_required
def export_tasks():
    tasks = Task.query.filter_by(user_id=current_user.id).all()
    task_data = [{
        'title': t.title,
        'description': t.description,
        'completed': t.completed,
        'due_date': t.due_date.strftime('%Y-%m-%d') if t.due_date else None,
        'priority': t.priority,
        'reminder_set': t.reminder_set
    } for t in tasks]
    log_action(current_user.id, "Exported tasks as JSON")
    return jsonify({'tasks': task_data})

@views.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = ProfileUpdateForm(obj=current_user)
    if form.validate_on_submit():
        user_by_email = User.query.filter(User.email == form.email.data, User.id != current_user.id).first()
        user_by_username = User.query.filter(User.username == form.username.data, User.id != current_user.id).first()
        if user_by_email:
            flash("Email already in use.", category='error')
        elif user_by_username:
            flash("Username already in use.", category='error')
        else:
            old_username = current_user.username
            current_user.email = form.email.data
            current_user.username = form.username.data
            current_user.profile_type = form.profile_type.data
            db.session.commit()
            flash("Profile updated successfully.", category='success')
            log_action(current_user.id, f"Updated profile from username '{old_username}' to '{current_user.username}'")
            return redirect(url_for('views.profile'))
    return render_template('profile.html', form=form)

@views.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = PasswordChangeForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.old_password.data):
            flash("Old password is incorrect.", category='error')
        else:
            current_user.set_password(form.new_password.data)
            db.session.commit()
            flash("Password changed successfully!", category='success')
            log_action(current_user.id, "Changed password")
            return redirect(url_for('views.profile'))

    return render_template('change_password.html', form=form)

@views.route('/tasks/complete/<int:id>', methods=['POST'])
@login_required
def toggle_task_completion(id):
    task = Task.query.get_or_404(id)
    if task.user_id != current_user.id:
        return jsonify({"error": "Unauthorized"}), 403
    task.completed = not task.completed
    db.session.commit()
    log_action(current_user.id, f"Toggled task completion for '{task.title}' to {task.completed}")
    return jsonify({"success": True, "completed": task.completed})

@views.route('/tasks/reminder/<int:id>', methods=['POST'])
@login_required
def toggle_task_reminder(id):
    task = Task.query.get_or_404(id)
    if task.user_id != current_user.id:
        return jsonify({"error": "Unauthorized"}), 403
    task.reminder_set = not task.reminder_set
    db.session.commit()
    log_action(current_user.id, f"Toggled reminder for task '{task.title}' to {task.reminder_set}")
    return jsonify({"success": True, "reminder_set": task.reminder_set})

# Bulk task operations
@views.route('/tasks/bulk-complete', methods=['POST'])
@login_required
def bulk_complete():
    task_ids = request.form.getlist('task_ids')
    updated = 0
    for tid in task_ids:
        task = Task.query.get(tid)
        if task and task.user_id == current_user.id and not task.completed:
            task.completed = True
            updated += 1
    db.session.commit()
    flash(f"Marked {updated} tasks as completed.", category='success')
    log_action(current_user.id, f"Bulk marked {updated} tasks as completed")
    return redirect(url_for('views.dashboard'))

@views.route('/tasks/bulk-delete', methods=['POST'])
@login_required
def bulk_delete():
    task_ids = request.form.getlist('task_ids')
    deleted = 0
    for tid in task_ids:
        task = Task.query.get(tid)
        if task and task.user_id == current_user.id:
            db.session.delete(task)
            deleted += 1
    db.session.commit()
    flash(f"Deleted {deleted} tasks.", category='info')
    log_action(current_user.id, f"Bulk deleted {deleted} tasks")
    return redirect(url_for('views.dashboard'))

# Advanced search page with detailed filters
@views.route('/tasks/search', methods=['GET', 'POST'])
@login_required
def task_search():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        completed = request.form.get('completed', 'any')
        priority = request.form.get('priority', 'any')

        query = Task.query.filter_by(user_id=current_user.id)

        if title:
            query = query.filter(Task.title.ilike(f'%{title}%'))
        if description:
            query = query.filter(Task.description.ilike(f'%{description}%'))
        if completed in ['true', 'false']:
            query = query.filter_by(completed=(completed == 'true'))
        if priority in ['1', '2', '3']:
            query = query.filter_by(priority=int(priority))

        results = query.order_by(Task.priority.asc(), Task.due_date.asc().nulls_last()).all()
        return render_template('task_search_results.html', tasks=results)
    else:
        return render_template('task_search.html')

@views.route('/tasks')
@login_required
def task_list():
    page = request.args.get('page', 1, type=int)
    tasks = Task.query.filter_by(user_id=current_user.id).paginate(page=page, per_page=10)
    return render_template('task_list.html', tasks=tasks)

# Custom error handlers
@views.app_errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@views.app_errorhandler(403)
def forbidden(e):
    return render_template('403.html'), 403

@views.app_errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500

@views.route('/')
def home():
    return render_template('home.html', title='Home')
