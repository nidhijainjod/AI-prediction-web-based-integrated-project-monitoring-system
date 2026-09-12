"""Feature engineering shared by model training and live prediction.

The feature vector represents the *current stage* of a project so the trained
regressors can extrapolate what the project's final cost/schedule outcome is
likely to be, based on patterns learned from many historical project stages.
"""

PRIORITY_ENCODING = {"Low": 1, "Medium": 2, "High": 3}
CATEGORIES = ["Software", "Infrastructure", "Construction", "Marketing", "Research", "General"]

FEATURE_NAMES = [
    "percent_complete",
    "cost_ratio",
    "schedule_ratio",
    "task_completion_ratio",
    "blocked_ratio",
    "overdue_ratio",
    "team_size",
    "priority_encoded",
    "category_encoded",
]

# Human-readable labels + the direction that means "worse" for narrative reasons.
FEATURE_META = {
    "cost_ratio": {
        "label": "spend pace vs. planned budget pace",
        "worse_is": "high",
        "reason_high": "Actual spend is running {pct:.0f}% ahead of the pace implied by planned budget for the current progress.",
        "reason_low": "Actual spend is comfortably within the planned budget pace.",
    },
    "schedule_ratio": {
        "label": "time elapsed vs. planned schedule pace",
        "worse_is": "high",
        "reason_high": "Elapsed time is running {pct:.0f}% ahead of the pace implied by the planned schedule for the current progress.",
        "reason_low": "Elapsed time is tracking close to the planned schedule.",
    },
    "blocked_ratio": {
        "label": "share of tasks currently blocked",
        "worse_is": "high",
        "reason_high": "{pct:.0f}% of tasks are currently blocked, stalling downstream work.",
        "reason_low": "Very few tasks are blocked.",
    },
    "overdue_ratio": {
        "label": "share of tasks past their planned end date",
        "worse_is": "high",
        "reason_high": "{pct:.0f}% of tasks are overdue against their planned end date.",
        "reason_low": "Task due dates are mostly being met.",
    },
    "task_completion_ratio": {
        "label": "share of tasks completed",
        "worse_is": "low",
        "reason_high": "Task completion is keeping pace.",
        "reason_low": "Only {pct:.0f}% of tasks are completed, lagging overall progress.",
    },
}


def encode_category(category):
    try:
        return CATEGORIES.index(category)
    except ValueError:
        return len(CATEGORIES) - 1


def encode_priority(priority):
    return PRIORITY_ENCODING.get(priority, 2)


def extract_features_dict(
    percent_complete,
    planned_budget,
    actual_cost_to_date,
    elapsed_days,
    planned_duration_days,
    task_count,
    completed_task_count,
    blocked_task_count,
    overdue_task_count,
    team_size,
    priority,
    category,
):
    pc = max(percent_complete / 100.0, 0.0001)
    safe_pc = max(pc, 0.05)
    budget = max(planned_budget, 1.0)
    duration = max(planned_duration_days, 1)

    cost_ratio = (actual_cost_to_date / budget) / safe_pc
    schedule_ratio = (elapsed_days / duration) / safe_pc
    task_completion_ratio = (completed_task_count / task_count) if task_count else pc
    blocked_ratio = (blocked_task_count / task_count) if task_count else 0.0
    overdue_ratio = (overdue_task_count / task_count) if task_count else 0.0

    return {
        "percent_complete": pc,
        "cost_ratio": cost_ratio,
        "schedule_ratio": schedule_ratio,
        "task_completion_ratio": task_completion_ratio,
        "blocked_ratio": blocked_ratio,
        "overdue_ratio": overdue_ratio,
        "team_size": team_size,
        "priority_encoded": encode_priority(priority),
        "category_encoded": encode_category(category),
    }


def features_for_project(project):
    return extract_features_dict(
        percent_complete=project.percent_complete or 0.0,
        planned_budget=project.planned_budget,
        actual_cost_to_date=project.actual_cost_to_date or 0.0,
        elapsed_days=project.elapsed_days,
        planned_duration_days=project.planned_duration_days,
        task_count=project.task_count,
        completed_task_count=project.completed_task_count,
        blocked_task_count=project.blocked_task_count,
        overdue_task_count=project.overdue_task_count,
        team_size=project.team_size or 1,
        priority=project.priority,
        category=project.category,
    )


def feature_vector(features_dict):
    return [features_dict[name] for name in FEATURE_NAMES]
