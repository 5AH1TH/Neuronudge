from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, TextAreaField, BooleanField, DateField, IntegerField, TimeField, SelectMultipleField, widgets
from wtforms.validators import InputRequired, Email, Length, Optional, NumberRange, ValidationError, EqualTo, DataRequired
from datetime import date, time, timedelta


PROFILE_CHOICES = [
    ('general', 'General'),
    ('adhd', 'ADHD'),
    ('dyslexia', 'Dyslexia'),
    ('custom', 'Customized')
]

#estimated_time = IntegerField("Estimated Time (minutes)", validators=[Optional()])
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
    profile_type = SelectField('Profile Type', choices=PROFILE_CHOICES, default='general')

    # 🔹 Feature checkboxes (kept, no removals)
    feature_timer = BooleanField('Per-task Timer (Start Task)')
    feature_focus_mode = BooleanField('Focus Mode Overlay')
    feature_scroll_autostart = BooleanField('Auto-scroll when starting a task')
    feature_task_stats = BooleanField('Task Stats')
    feature_task_timer = BooleanField('Task Timer')
    feature_deadline_tracker = BooleanField("Enable Deadline Tracker")
    feature_custom_colors = BooleanField('Custom Color Theme')
    feature_auto_reminders = BooleanField('Due Soon Reminders')
    feature_priority_sort = BooleanField("Enable Priority Sort")
    feature_task_export = BooleanField("Enable Task Export")
    feature_progress_graphs = BooleanField("Enable Progress Graphs")

    submit = SubmitField('Register')

    def get_selected_features(self):
        """Return list of selected features as strings"""
        features = []
        if self.feature_timer.data:
            features.append("timer")
        if self.feature_focus_mode.data:
            features.append("focus_mode")
        if self.feature_scroll_autostart.data:
            features.append("scroll_autostart")
        if self.feature_task_stats.data:
            features.append("task_stats")
        if self.feature_custom_colors.data:
            features.append("custom_colors")
        if self.feature_auto_reminders.data:
            features.append("auto_reminders")
        return features
    
class LoginForm(FlaskForm):
    email = StringField('Email', validators=[InputRequired(), Email()])
    password = PasswordField('Password', validators=[InputRequired()])
    submit = SubmitField('Login')
    remember_me = BooleanField('Remember Me')

class OnboardingForm(FlaskForm):
    focus_time = IntegerField("Focus Time", validators=[DataRequired()])
    break_time = IntegerField("Break Time", validators=[DataRequired()])
    notifications_enabled = BooleanField("Enable Notifications")

    selected_features = SelectMultipleField(
        "Choose Dashboard Features",
        choices=[
            ("timer", "Pomodoro Timer"),
            ("task_list", "Task List"),
            ("calendar", "Calendar View"),
            ("progress", "Progress Tracking"),
            ("rewards", "Reward System"),
            ("themes", "Custom Themes")
        ],
        option_widget=widgets.CheckboxInput(),
        widget=widgets.ListWidget(prefix_label=False)
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
    title = StringField("Title", validators=[DataRequired()])
    description = TextAreaField("Description")
    due_date = DateField("Due Date", validators=[DataRequired()])
    due_time = TimeField("Due Time (optional)", validators=[Optional()])
    submit = SubmitField("Save Task")
    reminder_set = BooleanField("Set Reminder?")

    priority = SelectField(
    "Priority",
    choices=[
        ("1", "High"),
        ("2", "Medium"),
        ("3", "Low"),
    ],
    default="2",
    validators=[DataRequired()]
)
    status = SelectField(
        "Status",
        choices=[("not_started", "Not Started"),
                 ("in_progress", "In Progress"),
                 ("completed", "Completed")],
        default="not_started"
    )

    def validate(self, extra_validators=None):
        """Custom validation for handling default time and past dates."""
        initial_validation = super(TaskForm, self).validate(extra_validators)
        if not initial_validation:
            return False

        # Handle missing due_time → default to 11:59 AM previous day
        if not self.due_time.data:
            default_time = time(11, 59)
            self.due_time.data = default_time

            # Shift date back by 1 day since time is "day before"
            if self.due_date.data:
                self.due_date.data = self.due_date.data - timedelta(days=1)

        return True
class ProfileUpdateForm(FlaskForm):
    username = StringField('Username', validators=[Optional(), Length(min=4, max=20)])
    email = StringField('Email', validators=[InputRequired(), Email()])
    profile_type = SelectField('Profile Type', choices=[('ADHD', 'ADHD'), ('Dyslexia', 'Dyslexia'), ('General', 'General')])
    submit = SubmitField('Update Profile')

    
class ChangePasswordForm(FlaskForm):
    current_password = PasswordField("Current Password", validators=[DataRequired()])
    new_password = PasswordField("New Password", validators=[DataRequired(), Length(min=6)])
    confirm_new_password = PasswordField(
        "Confirm New Password",
        validators=[DataRequired(), EqualTo("new_password", message="Passwords must match")],
    )

    def validate_confirm_password(self, field):
        if field.data != self.new_password.data:
            raise ValidationError("New passwords must match.")
        
    submit = SubmitField("Change Password")


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

