from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, TextAreaField, BooleanField, DateField, IntegerField
from wtforms.validators import InputRequired, Email, Length, Optional, NumberRange, ValidationError, EqualTo
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
    preference = TextAreaField('What would help you focus better?', validators=[Length(max=500)])
    completed = BooleanField('I have completed the onboarding process.')
    submit = SubmitField('Save Preferences')

class TaskForm(FlaskForm):
    title = StringField('Title', validators=[InputRequired(), Length(max=100)])
    description = TextAreaField('Description', validators=[Optional(), Length(max=1000)])
    completed = BooleanField('Completed')
    due_date = DateField('Due Date', format='%Y-%m-%d', validators=[Optional()])
    priority = SelectField('Priority', choices=[('1', 'High'), ('2', 'Medium'), ('3', 'Low')], default='3')
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
