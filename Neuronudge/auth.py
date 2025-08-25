# Neuronudge/auth.py
from flask import Blueprint, render_template, redirect, url_for, flash, request
from .forms import LoginForm, RegisterForm
from .models import User
from . import db
from flask_login import login_user, logout_user, login_required
from werkzeug.security import generate_password_hash

auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        # use the model's check_password helper
        if user and user.check_password(form.password.data):
            login_user(user)
            flash("Login successful!", category='success')
            return redirect(url_for('main.dashboard'))
        else:
            flash("Invalid credentials.", category='error')
    return render_template('login.html', form=form)

@auth.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()

    # debugging helpful prints (remove later if you want)
    if request.method == 'POST':
        print("✅ POST request received.")
        print("Form validation:", form.validate_on_submit())
        print("Form errors:", form.errors)
        print("Request.form:", dict(request.form))

    if form.validate_on_submit():
        existing_user = User.query.filter_by(email=form.email.data).first()
        if existing_user:
            flash("Email already registered.", category='error')
        else:
            hashed_password = generate_password_hash(form.password.data, method='pbkdf2:sha256', salt_length=16)
            new_user = User(
                name=form.name.data,
                email=form.email.data,
                username=form.username.data,
                password_hash=hashed_password,
                profile_type=form.profile_type.data,
                dashboard_features=form.get_selected_features(),

                # ✅ Save feature selections
                feature_task_timer=form.feature_task_timer.data,
                feature_task_stats=form.feature_task_stats.data,
                feature_focus_mode=form.feature_focus_mode.data,
                feature_deadline_tracker=form.feature_deadline_tracker.data,
                feature_priority_sort=form.feature_priority_sort.data,
                feature_task_export=form.feature_task_export.data,
                feature_progress_graphs=form.feature_progress_graphs.data
            )
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            flash("Registration successful!", category='success')

            # redirect to customized dashboard
            return redirect(url_for('main.dashboard_customized'))
    else:
        # If POST and there are errors, flash them so user sees why validation failed
        if request.method == 'POST' and form.errors:
            for field, errors in form.errors.items():
                for err in errors:
                    flash(f"{field}: {err}", category='error')

    return render_template('register.html', form=form)

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

@auth.route('/password_reset', methods=['GET', 'POST'])
def password_reset():
    if request.method == 'POST':
        email = request.form.get('email')
        flash("If this email is registered, you'll receive a password reset link.", 'info')
        return redirect(url_for('auth.login'))
    return render_template('password_reset.html')
