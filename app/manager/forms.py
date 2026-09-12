from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, FloatField, IntegerField, DateField
from wtforms.validators import DataRequired, Length, NumberRange, Optional

from app.models import PROJECT_STATUSES, TASK_STATUSES, PRIORITIES
from app.ml.features import CATEGORIES


class ProjectForm(FlaskForm):
    name = StringField("Project name", validators=[DataRequired(), Length(max=200)])
    description = TextAreaField("Description", validators=[Optional(), Length(max=4000)])
    client_name = StringField("Client", validators=[Optional(), Length(max=150)])
    category = SelectField("Category", choices=[(c, c) for c in CATEGORIES])
    priority = SelectField("Priority", choices=[(p, p) for p in PRIORITIES])
    status = SelectField("Status", choices=[(s, s) for s in PROJECT_STATUSES])
    planned_start_date = DateField("Planned start date", validators=[DataRequired()])
    planned_end_date = DateField("Planned end date", validators=[DataRequired()])
    actual_start_date = DateField("Actual start date", validators=[Optional()])
    actual_end_date = DateField("Actual end date", validators=[Optional()])
    planned_budget = FloatField("Planned budget ($)", validators=[DataRequired(), NumberRange(min=0)])
    team_size = IntegerField("Team size", validators=[DataRequired(), NumberRange(min=1, max=500)])

    def validate(self, extra_validators=None):
        ok = super().validate(extra_validators=extra_validators)
        if ok and self.planned_end_date.data and self.planned_start_date.data:
            if self.planned_end_date.data <= self.planned_start_date.data:
                self.planned_end_date.errors.append("End date must be after start date.")
                ok = False
        return ok


class TaskForm(FlaskForm):
    name = StringField("Task name", validators=[DataRequired(), Length(max=200)])
    description = TextAreaField("Description", validators=[Optional(), Length(max=4000)])
    assignee_id = SelectField("Assignee", coerce=int, validators=[Optional()])
    status = SelectField("Status", choices=[(s, s) for s in TASK_STATUSES])
    priority = SelectField("Priority", choices=[(p, p) for p in PRIORITIES])
    planned_start = DateField("Planned start", validators=[DataRequired()])
    planned_end = DateField("Planned end", validators=[DataRequired()])
    actual_start = DateField("Actual start", validators=[Optional()])
    actual_end = DateField("Actual end", validators=[Optional()])
    percent_complete = FloatField("Percent complete", validators=[DataRequired(), NumberRange(min=0, max=100)])
    estimated_cost = FloatField("Estimated cost ($)", validators=[DataRequired(), NumberRange(min=0)])
    actual_cost = FloatField("Actual cost ($)", validators=[DataRequired(), NumberRange(min=0)])
    estimated_hours = FloatField("Estimated hours", validators=[DataRequired(), NumberRange(min=0)])
    actual_hours = FloatField("Actual hours", validators=[DataRequired(), NumberRange(min=0)])
