from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, abort, current_app
from flask_login import login_required, current_user
from .models import Task, OnboardingPreferences, User
from . import db
from .forms import OnboardingForm, TaskForm, ProfileUpdateForm, PasswordChangeForm, RegisterForm, ChangePasswordForm
from datetime import datetime, time
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
import logging
import pytz
from datetime import timedelta
import os

PACIFIC = pytz.timezone('US/Pacific')

main = Blueprint("main", __name__)


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

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

@main.route('/dashboard')
@login_required
def dashboard():
    page = request.args.get('page', 1, type=int)
    per_page = 10

    filter_status = request.args.get('status', 'all')
    filter_priority = request.args.get('priority', 'all')
    search_term = request.args.get('search', '').strip()

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

    task_form = TaskForm()

    # Keep your recent_tasks exactly as-is
    recent_tasks = Task.query.filter_by(user_id=current_user.id).order_by(
        Task.priority.asc(),
        Task.due_date.asc().nulls_last()
    ).limit(10).all()

    onboarding = OnboardingPreferences.query.filter_by(user_id=current_user.id).first()

    profile_type = getattr(current_user, "profile_type", "general").lower()

    if profile_type == "dyslexia":
        dashboard_template = "dashboard_dyslexia.html"
    elif profile_type == "adhd":
        dashboard_template = "dashboard_adhd.html"
    elif profile_type == "custom":
        dashboard_template = "dashboard_customized.html"
    else:
        dashboard_template = "dashboard.html"

    
    # ============================
    # NEW: provide recent_activity
    # ============================

    ActivityLog = Task.query.filter_by(user_id=current_user.id).order_by(
        Task.updated_at.desc()
    ).limit(10).all()
    
    try:
        recent_activity = ActivityLog.query.filter_by(user_id=current_user.id) \
            .order_by(ActivityLog.timestamp.desc()) \
            .limit(10).all()
    except Exception:
        recent_activity = []

    # Fallback if no ActivityLog rows yet: synthesize simple activity items from Tasks
    if not recent_activity:
        class _SimpleActivity:
            __slots__ = ("description", "timestamp")
            def __init__(self, description, timestamp):
                self.description = description
                self.timestamp = timestamp

        task_feed = Task.query.filter_by(user_id=current_user.id) \
            .order_by(Task.updated_at.desc().nulls_last(), Task.created_at.desc().nulls_last()) \
            .limit(10).all()

        recent_activity = [
            _SimpleActivity(
                f"Task “{t.title}” — status: {t.status or ('completed' if t.completed else 'pending')}",
                (t.updated_at or t.created_at or datetime.utcnow())
            )
            for t in task_feed
        ]
    
    return render_template(
        dashboard_template,
        tasks=tasks,
        recent_tasks=recent_tasks,
        recent_activity=recent_activity,  # <-- pass it to ALL dashboards
        onboarding=onboarding,
        filter_status=filter_status,
        filter_priority=filter_priority,
        search_term=search_term,
        task_counts=task_counts,
        task_form=task_form,
        pytz=pytz,
        paginated_tasks=paginated_tasks,
        features=current_user.dashboard_features or []
    )


@main.route('/dashboard/custom', methods=['GET', 'POST'])
@login_required
def dashboard_customized():
    """
    Fully functional dashboard_customized route:
    - Shows paginated task table
    - Handles inline 'Add Task' form (TaskForm) POST
    - Computes task_counts, recent_tasks, paginated_tasks
    - Builds features list from booleans + dashboard_features JSON
    """
    # --- Forms ---
    task_form = TaskForm()

    # --- Handle inline add-task POST (from the modal or side form) ---
    if task_form.validate_on_submit():
        # compute due_date: treat date as PACIFIC end of day (23:59) and store UTC naive
        computed_due = None
        if getattr(task_form, 'due_date', None) and task_form.due_date.data:
            local_due = datetime.combine(task_form.due_date.data, time(23, 59))
            local_due = PACIFIC.localize(local_due)
            computed_due = local_due.astimezone(pytz.UTC).replace(tzinfo=None)
        else:
            # fallback: use onboarding focus time or default 25 minutes from now (pacific)
            prefs = OnboardingPreferences.query.filter_by(user_id=current_user.id).first()
            focus_minutes = int(prefs.focus_time) if prefs and prefs.focus_time else 25
            now_local = datetime.now(PACIFIC)
            local_due = now_local + timedelta(minutes=focus_minutes)
            computed_due = local_due.astimezone(pytz.UTC).replace(tzinfo=None)

        try:
            new_task = Task(
                title = task_form.title.data,
                description = getattr(task_form, 'description', None) and task_form.description.data or '',
                completed = False,
                due_date = computed_due,
                priority = int(task_form.priority.data) if task_form.priority.data else None,
                reminder_set = bool(getattr(task_form, 'reminder_set', False) and task_form.reminder_set.data),
                user_id = current_user.id
            )
            db.session.add(new_task)
            db.session.commit()
            flash("Task created", category='success')
            return redirect(url_for('main.dashboard_customized'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception("Error creating task")
            flash(f"Could not create task: {e}", category='error')
            # don't return here; continue to render dashboard so user sees errors

    # --- Pagination / filters / query building ---
    page = request.args.get('page', 1, type=int)
    per_page = 10

    filter_status = request.args.get('status', 'all')
    filter_priority = request.args.get('priority', 'all')
    search_term = request.args.get('search', '').strip()

    base_query = Task.query.filter_by(user_id=current_user.id)

    if filter_status == 'completed':
        base_query = base_query.filter_by(completed=True)
    elif filter_status == 'pending':
        base_query = base_query.filter_by(completed=False)

    if filter_priority in ['1', '2', '3']:
        base_query = base_query.filter_by(priority=int(filter_priority))

    if search_term:
        # use ilike if supported; fallback to like in SQLite
        try:
            base_query = base_query.filter(Task.title.ilike(f'%{search_term}%'))
        except Exception:
            base_query = base_query.filter(Task.title.like(f'%{search_term}%'))

    # ordering: priority asc, then due_date ascending (nulls last)
    try:
        ordered_query = base_query.order_by(Task.priority.asc(), Task.due_date.asc().nulls_last())
    except Exception:
        # if `.nulls_last()` not available, just order by due_date asc
        ordered_query = base_query.order_by(Task.priority.asc(), Task.due_date.asc())

    paginated_tasks = ordered_query.paginate(page=page, per_page=per_page, error_out=False)

    # full list for some widgets (non-paginated)
    tasks_all = Task.query.filter_by(user_id=current_user.id).all()

    # --- recent tasks and counts ---
    recent_tasks = Task.query.filter_by(user_id=current_user.id).order_by(Task.created_at.desc()).limit(10).all()

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

    onboarding = OnboardingPreferences.query.filter_by(user_id=current_user.id).first()

    # --- Build features list (honor DB JSON if present plus boolean flags) ---
    features = set()
    # If you store a JSON array in current_user.dashboard_features use it
    try:
        if current_user.dashboard_features:
            # if it's stored as JSON list already, it should be usable; otherwise guard
            if isinstance(current_user.dashboard_features, (list, tuple, set)):
                features.update(current_user.dashboard_features)
            else:
                # if it's a JSON string, try to parse
                import json
                try:
                    parsed = json.loads(current_user.dashboard_features)
                    if isinstance(parsed, (list, tuple, set)):
                        features.update(parsed)
                except Exception:
                    # ignore parsing errors
                    pass
    except Exception:
        pass

    # Map boolean user flags to feature keys used by template
    if getattr(current_user, 'feature_timer', False):
        features.add('timer')
    if getattr(current_user, 'feature_focus_mode', False):
        features.add('focus_mode')
    if getattr(current_user, 'feature_scroll_autostart', False):
        features.add('scroll_autostart')
    if getattr(current_user, 'feature_task_stats', False):
        features.add('task_stats')
    if getattr(current_user, 'feature_task_timer', False):
        features.add('task_timer')
    if getattr(current_user, 'feature_deadline_tracker', False):
        features.add('deadline_tracker')
    if getattr(current_user, 'feature_custom_colors', False):
        features.add('custom_colors')
    if getattr(current_user, 'feature_auto_reminders', False):
        features.add('auto_reminders')
    if getattr(current_user, 'feature_priority_sort', False):
        features.add('priority_sort')
    if getattr(current_user, 'feature_task_export', False):
        features.add('task_export')
    if getattr(current_user, 'feature_progress_graphs', False):
        features.add('progress_graphs')

    # Ensure features is a list before sending to template
    features = sorted(list(features))

    return render_template(
        'dashboard_customized.html',
        user=current_user,
        tasks=tasks_all,
        recent_tasks=recent_tasks,
        task_counts=task_counts,
        filter_status=filter_status,
        filter_priority=filter_priority,
        search_term=search_term,
        paginated_tasks=paginated_tasks,
        onboarding=onboarding,
        features=features,
        task_form=task_form
    )



@main.route('/onboarding', methods=['GET', 'POST'])
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
        return redirect(url_for('main.dashboard'))
    
    if existing:
        form.focus_time.data = existing.focus_time
        form.break_time.data = existing.break_time
        form.notifications_enabled.data = existing.notifications_enabled

    return render_template('onboarding.html', form=form)

@main.route('/task/new', methods=['GET', 'POST'])
@login_required
def create_task():
    form = TaskForm()
    if form.validate_on_submit():
        prefs = OnboardingPreferences.query.filter_by(user_id=current_user.id).first()

        computed_due = None

        if form.due_date.data:
            # Treat the input date as Pacific local date at 23:59
            local_due = datetime.combine(form.due_date.data, time(23, 59))
            local_due = PACIFIC.localize(local_due)

            # Convert to UTC for storage in DB
            computed_due = local_due.astimezone(pytz.UTC).replace(tzinfo=None)
        else:
            # No due date provided, use onboarding focus time if available
            now_local = datetime.now(PACIFIC)
            focus_minutes = int(prefs.focus_time) if prefs and prefs.focus_time else 25
            local_due = now_local + timedelta(minutes=focus_minutes)
            computed_due = local_due.astimezone(pytz.UTC).replace(tzinfo=None)

        # Create the task with all features intact
        new_task = Task(
            title=form.title.data,
            description=form.description.data,
            completed=(form.status.data == "completed"),
            due_date=computed_due,
            priority=int(form.priority.data),
            reminder_set=form.reminder_set.data,
            user_id=current_user.id
        )

        db.session.add(new_task)
        db.session.commit()

        flash("Task added successfully!", category='success')
        log_action(current_user.id, f"Created task: {new_task.title}, date: {computed_due}")
        return redirect(url_for('main.dashboard'))

    return render_template('create_task.html', form=form)


@main.route('/task/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_task(id):
    task = Task.query.get_or_404(id)
    if task.user_id != current_user.id:
        flash("Unauthorized access.", category='error')
        abort(403)

    form = TaskForm(obj=task)

    # Preload priority and status fields for GET request
    if request.method == 'GET':
        form.priority.data = str(task.priority)
        form.status.data = "completed" if task.completed else "not_started"

    if form.validate_on_submit():
        old_title = task.title
        task.title = form.title.data
        task.description = form.description.data
        task.completed = (form.status.data == "completed")

        if form.due_date.data:
            # Treat the input date as Pacific local date at 23:59
            local_due = datetime.combine(form.due_date.data, time(23, 59))
            local_due = PACIFIC.localize(local_due)

            # Convert to UTC for storage
            task.due_date = local_due.astimezone(pytz.UTC).replace(tzinfo=None)

        # Store priority as integer and update reminder
        task.priority = int(form.priority.data)
        task.reminder_set = form.reminder_set.data

        db.session.commit()

        flash("Task updated successfully!", category='success')
        log_action(current_user.id, f"Edited task from '{old_title}' to '{task.title}'")
        return redirect(url_for('main.dashboard'))

    return render_template('edit_task.html', form=form, task=task)


@main.route('/task/delete/<int:id>', methods=['POST'])
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

    return redirect(url_for('main.dashboard'))


@main.route('/tasks/export')
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

@main.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = ProfileUpdateForm(obj=current_user)
    change_password_form = ChangePasswordForm()
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
            return redirect(url_for('main.profile'))
    return render_template('profile.html', form=form, change_password_form=change_password_form)

@main.route('/change-password', methods=['GET', 'POST'])
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
            return redirect(url_for('main.profile'))

    return render_template('change_password.html', form=form)

@main.route('/tasks/complete/<int:id>', methods=['POST'])
@login_required
def toggle_task_completion(id):
    task = Task.query.get_or_404(id)
    if task.user_id != current_user.id:
        return jsonify({"error": "Unauthorized"}), 403
    task.completed = not task.completed
    db.session.commit()
    log_action(current_user.id, f"Toggled task completion for '{task.title}' to {task.completed}")
    return jsonify({"success": True, "completed": task.completed})

@main.route('/tasks/reminder/<int:id>', methods=['POST'])
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
@main.route('/tasks/bulk-complete', methods=['POST'])
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
    return redirect(url_for('main.dashboard'))

@main.route('/tasks/bulk-delete', methods=['POST'])
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
    return redirect(url_for('main.dashboard'))

# Advanced search page with detailed filters
@main.route('/tasks/search', methods=['GET', 'POST'])
@login_required
def task_search():
    title = request.args.get('title', '').strip()
    description = request.args.get('description', '').strip()
    completed = request.args.get('completed', 'any')
    priority = request.args.get('priority', 'any')

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

    return render_template('task_search.html', results=results)

@main.route('/tasks')
@login_required
def task_list():
    page = request.args.get('page', 1, type=int)
    tasks = Task.query.filter_by(user_id=current_user.id).paginate(page=page, per_page=10)
    return render_template('task_list.html', tasks=tasks)

@main.route('/upload_avatar', methods=['POST'])
@login_required
def upload_avatar():
    if 'avatar' not in request.files:
        flash("No file part.", "danger")
        return redirect(url_for('main.profile'))

    file = request.files['avatar']
    if file.filename == '':
        flash("No selected file.", "warning")
        return redirect(url_for('main.profile'))

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Save URL in DB (relative path for static serving)
        current_user.avatar_url = url_for('static', filename=f'uploads/{filename}')
        db.session.commit()

        flash("Avatar updated successfully!", "success")
        return redirect(url_for('main.profile'))

    flash("Invalid file type. Allowed: png, jpg, jpeg, gif", "danger")
    return redirect(url_for('main.profile'))

@main.route('/task/update_status/<int:id>', methods=['POST'])
@login_required
def update_status(id):
    task = Task.query.get_or_404(id)
    data = request.get_json()
    new_status = data.get('status')
    if new_status in ['not started', 'in progress', 'completed']:
        task.status = new_status
        if new_status == 'completed':
            task.completed = True
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'success': False}), 400

# Custom error handlers
@main.app_errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@main.app_errorhandler(403)
def forbidden(e):
    return render_template('403.html'), 403

@main.app_errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500

@main.route('/')
def home():
    return render_template('home.html', title='Home')
