import json
from datetime import datetime, date

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db

ROLE_ADMIN = "admin"
ROLE_MANAGER = "manager"

PROJECT_STATUSES = ["Planning", "In Progress", "On Hold", "Completed", "Cancelled"]
TASK_STATUSES = ["Not Started", "In Progress", "Blocked", "Completed"]
PRIORITIES = ["Low", "Medium", "High"]
RISK_LEVELS = ["Low", "Medium", "High", "Critical"]


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default=ROLE_MANAGER)
    is_active_flag = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    projects = db.relationship(
        "Project", back_populates="manager", foreign_keys="Project.manager_id"
    )
    assigned_tasks = db.relationship(
        "Task", back_populates="assignee", foreign_keys="Task.assignee_id"
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == ROLE_ADMIN

    @property
    def is_active(self):
        return self.is_active_flag

    def __repr__(self):
        return f"<User {self.email} ({self.role})>"


class Project(db.Model):
    __tablename__ = "projects"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default="")
    client_name = db.Column(db.String(150), default="")
    category = db.Column(db.String(80), default="General")
    priority = db.Column(db.String(20), default="Medium")
    status = db.Column(db.String(30), default="Planning")

    manager_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    planned_start_date = db.Column(db.Date, nullable=False)
    planned_end_date = db.Column(db.Date, nullable=False)
    actual_start_date = db.Column(db.Date, nullable=True)
    actual_end_date = db.Column(db.Date, nullable=True)

    planned_budget = db.Column(db.Float, nullable=False, default=0.0)
    team_size = db.Column(db.Integer, default=1)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # --- cached rollups (recomputed whenever tasks change) ---
    percent_complete = db.Column(db.Float, default=0.0)
    actual_cost_to_date = db.Column(db.Float, default=0.0)

    # --- AI prediction fields (recomputed by app.ml.predictor) ---
    predicted_final_cost = db.Column(db.Float, nullable=True)
    predicted_overrun_pct = db.Column(db.Float, nullable=True)
    predicted_delay_days = db.Column(db.Float, nullable=True)
    predicted_completion_date = db.Column(db.Date, nullable=True)
    risk_score = db.Column(db.Float, nullable=True)
    risk_level = db.Column(db.String(20), nullable=True)
    risk_reasons_json = db.Column(db.Text, default="[]")
    recommendations_json = db.Column(db.Text, default="[]")
    last_predicted_at = db.Column(db.DateTime, nullable=True)

    manager = db.relationship("User", back_populates="projects", foreign_keys=[manager_id])
    tasks = db.relationship(
        "Task", back_populates="project", cascade="all, delete-orphan", order_by="Task.planned_end"
    )
    snapshots = db.relationship(
        "ProjectSnapshot",
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="ProjectSnapshot.snapshot_date",
    )

    # ---- convenience helpers ----
    @property
    def risk_reasons(self):
        try:
            return json.loads(self.risk_reasons_json or "[]")
        except (TypeError, ValueError):
            return []

    @risk_reasons.setter
    def risk_reasons(self, value):
        self.risk_reasons_json = json.dumps(value or [])

    @property
    def recommendations(self):
        try:
            return json.loads(self.recommendations_json or "[]")
        except (TypeError, ValueError):
            return []

    @recommendations.setter
    def recommendations(self, value):
        self.recommendations_json = json.dumps(value or [])

    @property
    def planned_duration_days(self):
        return max((self.planned_end_date - self.planned_start_date).days, 1)

    @property
    def elapsed_days(self):
        start = self.actual_start_date or self.planned_start_date
        today = date.today()
        return max((today - start).days, 0)

    @property
    def is_overdue(self):
        return self.status not in ("Completed", "Cancelled") and date.today() > self.planned_end_date

    @property
    def task_count(self):
        return len(self.tasks)

    @property
    def completed_task_count(self):
        return sum(1 for t in self.tasks if t.status == "Completed")

    @property
    def blocked_task_count(self):
        return sum(1 for t in self.tasks if t.status == "Blocked")

    @property
    def overdue_task_count(self):
        return sum(1 for t in self.tasks if t.is_overdue)

    def recompute_rollups(self):
        """Recalculate percent_complete and actual_cost_to_date from tasks."""
        tasks = self.tasks
        if tasks:
            self.percent_complete = round(sum(t.percent_complete for t in tasks) / len(tasks), 1)
            self.actual_cost_to_date = round(sum(t.actual_cost or 0 for t in tasks), 2)
        else:
            self.percent_complete = 0.0
            self.actual_cost_to_date = 0.0

    def __repr__(self):
        return f"<Project {self.name}>"


class Task(db.Model):
    __tablename__ = "tasks"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default="")
    assignee_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    status = db.Column(db.String(30), default="Not Started")
    priority = db.Column(db.String(20), default="Medium")

    planned_start = db.Column(db.Date, nullable=False)
    planned_end = db.Column(db.Date, nullable=False)
    actual_start = db.Column(db.Date, nullable=True)
    actual_end = db.Column(db.Date, nullable=True)

    percent_complete = db.Column(db.Float, default=0.0)
    estimated_cost = db.Column(db.Float, default=0.0)
    actual_cost = db.Column(db.Float, default=0.0)
    estimated_hours = db.Column(db.Float, default=0.0)
    actual_hours = db.Column(db.Float, default=0.0)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = db.relationship("Project", back_populates="tasks")
    assignee = db.relationship("User", back_populates="assigned_tasks", foreign_keys=[assignee_id])

    @property
    def is_overdue(self):
        return self.status != "Completed" and date.today() > self.planned_end

    def __repr__(self):
        return f"<Task {self.name}>"


class ProjectSnapshot(db.Model):
    """Point-in-time history used for trend charts and as ML training/feature context."""

    __tablename__ = "project_snapshots"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)
    snapshot_date = db.Column(db.Date, nullable=False, default=date.today)

    percent_complete = db.Column(db.Float, default=0.0)
    actual_cost_to_date = db.Column(db.Float, default=0.0)
    planned_cost_to_date = db.Column(db.Float, default=0.0)
    risk_score = db.Column(db.Float, nullable=True)

    project = db.relationship("Project", back_populates="snapshots")
