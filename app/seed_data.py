"""Demo data generation, shared by the `seed.py` CLI script and the
serverless auto-seed bootstrap used when running on an ephemeral host
(e.g. Vercel) where the database starts empty on every cold start.
"""
import random
from datetime import date, timedelta

from app.extensions import db
from app.models import User, Project, Task, ProjectSnapshot, ROLE_ADMIN, ROLE_MANAGER
from app.ml.predictor import recompute_and_store

random.seed(7)

TASK_NAME_POOL = {
    "Software": [
        "Requirements Gathering", "System Architecture Design", "Database Schema Design",
        "Backend API Development", "Frontend UI Development", "Third-Party Integration",
        "Unit & Integration Testing", "UAT & Bug Fixes", "Deployment & Go-Live", "Post-Launch Support",
    ],
    "Infrastructure": [
        "Site Survey & Assessment", "Hardware Procurement", "Network Design",
        "Installation - Phase 1", "Installation - Phase 2", "Configuration & Testing",
        "Staff Training", "Cutover & Go-Live", "Legacy System Decommission",
    ],
    "Construction": [
        "Site Preparation", "Foundation Work", "Structural Framing", "Electrical Rough-In",
        "Plumbing Rough-In", "Interior Finishing", "Inspection & Compliance", "Final Walkthrough",
    ],
    "Marketing": [
        "Brand Discovery Workshop", "Content Strategy", "Visual Design Concepts",
        "Website Development", "SEO Optimization", "Content Migration",
        "QA & Cross-Browser Testing", "Launch Campaign",
    ],
    "Research": [
        "Literature Review", "Survey Design", "Data Collection", "Data Analysis",
        "Stakeholder Interviews", "Draft Report", "Peer Review", "Final Report Publication",
    ],
    "General": [
        "Kickoff & Planning", "Requirements Definition", "Execution Phase 1",
        "Execution Phase 2", "Quality Review", "Stakeholder Sign-Off", "Closure",
    ],
}

NARRATIVES = {
    "healthy": dict(cost_ratio=1.0, schedule_ratio=1.0, blocked_frac=0.0, overdue_frac=0.08),
    "moderate": dict(cost_ratio=1.15, schedule_ratio=1.12, blocked_frac=0.15, overdue_frac=0.2),
    "at_risk": dict(cost_ratio=1.3, schedule_ratio=1.28, blocked_frac=0.25, overdue_frac=0.35),
    "critical": dict(cost_ratio=1.55, schedule_ratio=1.5, blocked_frac=0.35, overdue_frac=0.45),
    "early": dict(cost_ratio=1.02, schedule_ratio=1.0, blocked_frac=0.0, overdue_frac=0.05),
}

TODAY = date.today()

PROJECT_DEFS = [
    dict(
        name="Core Banking Platform Migration", category="Software", client="Global Trust Bank",
        priority="High", manager_idx=0, start_offset=-150, duration=240, budget=850000, team=14,
        narrative="critical", num_tasks=10, status="In Progress",
    ),
    dict(
        name="Retail POS Rollout", category="Infrastructure", client="Meridian Retail Group",
        priority="High", manager_idx=1, start_offset=-90, duration=150, budget=420000, team=9,
        narrative="at_risk", num_tasks=9, status="In Progress",
    ),
    dict(
        name="Corporate Website Redesign", category="Marketing", client="Atlas & Finch Co.",
        priority="Medium", manager_idx=2, start_offset=-60, duration=100, budget=95000, team=5,
        narrative="healthy", num_tasks=8, status="In Progress",
    ),
    dict(
        name="Warehouse Automation Upgrade", category="Infrastructure", client="Northbridge Logistics",
        priority="High", manager_idx=3, start_offset=-200, duration=220, budget=1250000, team=18,
        narrative="critical", num_tasks=9, status="In Progress",
    ),
    dict(
        name="Customer Mobile App v2", category="Software", client="Finwise Payments",
        priority="Medium", manager_idx=0, start_offset=-70, duration=130, budget=310000, team=8,
        narrative="moderate", num_tasks=10, status="In Progress",
    ),
    dict(
        name="New Office Campus - Phase 1", category="Construction", client="Helios Energy Corp",
        priority="High", manager_idx=4, start_offset=-180, duration=300, budget=2100000, team=22,
        narrative="at_risk", num_tasks=8, status="In Progress",
    ),
    dict(
        name="Market Expansion Research Study", category="Research", client="Solace Consumer Goods",
        priority="Low", manager_idx=2, start_offset=-45, duration=90, budget=60000, team=4,
        narrative="healthy", num_tasks=8, status="In Progress",
    ),
    dict(
        name="HR Analytics Dashboard", category="Software", client="Internal - HR Department",
        priority="Medium", manager_idx=1, start_offset=-20, duration=100, budget=140000, team=6,
        narrative="early", num_tasks=8, status="In Progress",
    ),
]


def make_users():
    admin = User(name="Ananya Sharma", email="admin@projectai.com", role=ROLE_ADMIN)
    admin.set_password("Admin@123")

    managers = [
        User(name="Priya Menon", email="priya.manager@projectai.com", role=ROLE_MANAGER),
        User(name="Rahul Verma", email="rahul.manager@projectai.com", role=ROLE_MANAGER),
        User(name="Sofia Alvarez", email="sofia.manager@projectai.com", role=ROLE_MANAGER),
        User(name="James Whitfield", email="james.manager@projectai.com", role=ROLE_MANAGER),
        User(name="Kenji Tanaka", email="kenji.manager@projectai.com", role=ROLE_MANAGER),
    ]
    for m in managers:
        m.set_password("Manager@123")

    db.session.add(admin)
    for m in managers:
        db.session.add(m)
    db.session.flush()
    return admin, managers


def _task_slices(planned_start, planned_end, num_tasks):
    total_days = max((planned_end - planned_start).days, num_tasks)
    slice_len = total_days / num_tasks
    slices = []
    for i in range(num_tasks):
        s = planned_start + timedelta(days=round(i * slice_len))
        e = planned_start + timedelta(days=round((i + 1) * slice_len))
        if e <= s:
            e = s + timedelta(days=1)
        slices.append((s, e))
    return slices


def generate_tasks(project, narrative_key, num_tasks, managers):
    params = NARRATIVES[narrative_key]
    names = TASK_NAME_POOL.get(project.category, TASK_NAME_POOL["General"])
    names = (names * ((num_tasks // len(names)) + 1))[:num_tasks]

    slices = _task_slices(project.planned_start_date, project.planned_end_date, num_tasks)
    past_indices = [i for i, (s, e) in enumerate(slices) if e <= TODAY]
    current_indices = [i for i, (s, e) in enumerate(slices) if s <= TODAY < e]

    blocked_count = min(round(num_tasks * params["blocked_frac"]), len(past_indices))
    overdue_count = min(round(num_tasks * params["overdue_frac"]), max(len(past_indices) - blocked_count, 0))

    # Most-recent past tasks are the ones still struggling (blocked / overdue-in-progress);
    # earlier ones are the completed backlog.
    blocked_set = set(past_indices[-blocked_count:]) if blocked_count else set()
    remaining_past = [i for i in past_indices if i not in blocked_set]
    overdue_set = set(remaining_past[-overdue_count:]) if overdue_count else set()

    estimated_cost_each = round(project.planned_budget / num_tasks, 2)
    cost_ratio = params["cost_ratio"]

    for i, (slice_start, slice_end) in enumerate(slices):
        status = "Not Started"
        percent_complete = 0.0
        actual_start = None
        actual_end = None

        if i in blocked_set:
            status = "Blocked"
            percent_complete = round(random.uniform(15, 55), 1)
            actual_start = slice_start
        elif i in overdue_set:
            status = "In Progress"
            percent_complete = round(random.uniform(40, 85), 1)
            actual_start = slice_start
        elif i in current_indices:
            status = "In Progress"
            frac = (TODAY - slice_start).days / max((slice_end - slice_start).days, 1)
            percent_complete = round(max(min(frac, 1), 0) * 100, 1)
            actual_start = slice_start
        elif i in past_indices:
            status = "Completed"
            percent_complete = 100.0
            actual_start = slice_start
            actual_end = slice_end
        # else future task: stays Not Started / 0%

        estimated_hours = round(estimated_cost_each / 95.0, 1)
        actual_cost = round(estimated_cost_each * (percent_complete / 100.0) * cost_ratio, 2) if percent_complete else 0.0
        actual_hours = round(estimated_hours * (percent_complete / 100.0) * random.uniform(0.9, 1.3), 1) if percent_complete else 0.0

        task = Task(
            name=names[i],
            description=f"{names[i]} for {project.name}.",
            assignee_id=random.choice(managers).id,
            status=status,
            priority=random.choice(["Low", "Medium", "High"]),
            planned_start=slice_start,
            planned_end=slice_end,
            actual_start=actual_start,
            actual_end=actual_end,
            percent_complete=percent_complete,
            estimated_cost=estimated_cost_each,
            actual_cost=actual_cost,
            estimated_hours=estimated_hours,
            actual_hours=actual_hours,
        )
        project.tasks.append(task)


def generate_history(project, num_points=12):
    start = project.planned_start_date
    end = min(TODAY, project.planned_end_date)
    if end <= start:
        return
    total_days = (end - start).days
    final_pc = project.percent_complete or 0.0
    final_cost = project.actual_cost_to_date or 0.0

    for i in range(1, num_points + 1):
        frac = i / num_points
        snap_date = start + timedelta(days=round(total_days * frac))
        ramp = frac ** 0.85
        db.session.add(
            ProjectSnapshot(
                project_id=project.id,
                snapshot_date=snap_date,
                percent_complete=round(final_pc * ramp, 1),
                actual_cost_to_date=round(final_cost * ramp, 2),
                planned_cost_to_date=round(project.planned_budget * frac, 2),
                risk_score=None,
            )
        )


def build_projects(managers):
    for pdef in PROJECT_DEFS:
        planned_start = TODAY + timedelta(days=pdef["start_offset"])
        planned_end = planned_start + timedelta(days=pdef["duration"])
        project = Project(
            name=pdef["name"],
            description=f"{pdef['name']} engagement for {pdef['client']}.",
            client_name=pdef["client"],
            category=pdef["category"],
            priority=pdef["priority"],
            status=pdef["status"],
            manager_id=managers[pdef["manager_idx"]].id,
            planned_start_date=planned_start,
            planned_end_date=planned_end,
            actual_start_date=planned_start,
            planned_budget=pdef["budget"],
            team_size=pdef["team"],
        )
        db.session.add(project)
        db.session.flush()

        generate_tasks(project, pdef["narrative"], pdef["num_tasks"], managers)
        project.recompute_rollups()
        db.session.flush()

        generate_history(project)
        recompute_and_store(project, record_snapshot=False)

    db.session.commit()


def reset_and_seed():
    """Destructive: drops all tables and rebuilds the full demo dataset. CLI use only."""
    from app.ml.train import train_and_save

    db.drop_all()
    db.create_all()
    train_and_save()
    admin, managers = make_users()
    build_projects(managers)


def ensure_demo_data():
    """Idempotent bootstrap for ephemeral hosts: creates tables and seeds demo
    data only if the database is empty. Safe to call on every cold start."""
    db.create_all()
    if User.query.count() == 0:
        admin, managers = make_users()
        build_projects(managers)
