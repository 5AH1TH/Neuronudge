from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, TextAreaField, BooleanField, DateField, IntegerField
from wtforms.validators import InputRequired, Email, Length, Optional, NumberRange, ValidationError, EqualTo, DataRequired
from datetime import date

print("Loading forms.py from:", __file__)

class RegisterForm(FlaskForm):
    name = StringField('Full Name', validators=[InputRequired(), Length(min=2, max=50)])
    email = StringField('Email', validators=[InputRequired(), Email()])
    username = StringField('Username', validators=[Optional(), Length(min=4, max=20)])
    password = PasswordField('Password', validators=[InputRequired(), Length(min=8)])
    confirm_password = PasswordField('Confirm Password', validators=[
        InputRequired(),
        EqualTo('password', message='Passwords must match')
    ])
    profile_type = SelectField('Profile Type', choices=[('ADHD', 'ADHD'), ('Dyslexia', 'Dyslexia'), ('General', 'General')])
    submit = SubmitField('Register')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[InputRequired(), Email()])
    password = PasswordField('Password', validators=[InputRequired()])
    submit = SubmitField('Login')
    remember_me = BooleanField('Remember Me')

class OnboardingForm(FlaskForm):
    focus_time = IntegerField(
        'Preferred Focus Time (minutes)',
        validators=[
            DataRequired(message="Please enter your preferred focus time."),
            NumberRange(min=5, max=180, message="Focus time must be between 5 and 180 minutes.")
        ]
    )

    break_time = IntegerField(
        'Preferred Break Time (minutes)',
        validators=[
            DataRequired(message="Please enter your preferred break time."),
            NumberRange(min=1, max=60, message="Break time must be between 1 and 60 minutes.")
        ]
    )

    notifications_enabled = BooleanField(
        'Enable Notifications',
        default=False
    )

    submit = SubmitField('Save Preferences')

class TaskForm(FlaskForm):
    title = StringField('Title', validators=[InputRequired(), Length(max=100)])
    description = TextAreaField('Description', validators=[Optional(), Length(max=1000)])
    completed = BooleanField('Completed')
    due_date = DateField('Due Date', format='%Y-%m-%d', validators=[Optional()])
    priority = SelectField('Priority', choices=[
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High')
    ])
    reminder_set = BooleanField('Set Reminder')
    submit = SubmitField('Save Task')

    def validate_due_date(self, field):
        if field.data and field.data < date.today():
            raise ValidationError("Due date cannot be in the past.")

class ProfileUpdateForm(FlaskForm):
    username = StringField('Username', validators=[Optional(), Length(min=4, max=20)])
    email = StringField('Email', validators=[InputRequired(), Email()])
    profile_type = SelectField('Profile Type', choices=[('ADHD', 'ADHD'), ('Dyslexia', 'Dyslexia'), ('General', 'General')])
    submit = SubmitField('Update Profile')

class PasswordChangeForm(FlaskForm):
    old_password = PasswordField('Old Password', validators=[InputRequired()])
    new_password = PasswordField('New Password', validators=[InputRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm New Password', validators=[InputRequired()])
    submit = SubmitField('Change Password')

    def validate_confirm_password(self, field):
        if field.data != self.new_password.data:
            raise ValidationError("New passwords must match.")

class PreferencesForm(FlaskForm):
    focus_time = IntegerField(
        "Preferred Focus Time (minutes)",
        validators=[
            DataRequired(),
            NumberRange(min=5, max=180, message="Focus time must be between 5 and 180 minutes.")
        ]
    )
    break_time = IntegerField(
        "Preferred Break Time (minutes)",
        validators=[
            DataRequired(),
            NumberRange(min=1, max=60, message="Break time must be between 1 and 60 minutes.")
        ]
    )
    notifications_enabled = BooleanField("Enable Notifications")
    submit = SubmitField("Save Preferences")