from flask import Blueprint, render_template, redirect, url_for, flash, request
from .forms import LoginForm, RegisterForm
from .models import User
from . import db
from flask_login import login_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash

auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user)
            flash("Login successful!", category='success')
            return redirect(url_for('views.dashboard'))
        else:
            flash("Invalid credentials.", category='error')
    return render_template('login.html', form=form)

@auth.route('/register', methods=['GET', 'POST'])
def register():
    raise Exception("Something went wrong! This is Sahith!")

    form = RegisterForm()

    if request.method == 'POST':
        print("✅ POST request received.")
        print("Form validation:", form.validate_on_submit())
        print("Errors:", form.errors)

    if form.validate_on_submit():
        existing_user = User.query.filter_by(email=form.email.data).first()
        if existing_user:
            flash("Email already registered.", category='error')
        else:
            hashed_password = generate_password_hash(form.password.data, method='sha256')
            new_user = User(
                email=form.email.data,
                username=form.username.data,
                password_hash=hashed_password,
                profile_type=form.profile_type.data
            )
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            flash("Registration successful!", category='success')
            return redirect(url_for('views.dashboard'))

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
