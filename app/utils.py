from functools import wraps

from flask import abort
from flask_login import current_user


def role_required(*roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            if current_user.role not in roles:
                abort(403)
            return view_func(*args, **kwargs)

        return wrapped

    return decorator


def admin_required(view_func):
    return role_required("admin")(view_func)


def manager_required(view_func):
    return role_required("manager", "admin")(view_func)


def portfolio_summary(projects):
    """Aggregate stats used by both the admin dashboard and the public landing page."""
    total = len(projects)
    active_projects = [p for p in projects if p.status not in ("Completed", "Cancelled")]

    def risk_bucket(level):
        return len([p for p in active_projects if p.risk_level == level])

    at_risk = risk_bucket("High") + risk_bucket("Critical")
    total_planned_budget = sum(p.planned_budget for p in projects)
    total_predicted_cost = sum(p.predicted_final_cost or p.planned_budget for p in projects)
    avg_overrun = (
        sum(p.predicted_overrun_pct or 0 for p in active_projects) / len(active_projects)
        if active_projects
        else 0
    )
    avg_delay = (
        sum(p.predicted_delay_days or 0 for p in active_projects) / len(active_projects)
        if active_projects
        else 0
    )

    return {
        "total_projects": total,
        "active_projects": len(active_projects),
        "completed_projects": len([p for p in projects if p.status == "Completed"]),
        "at_risk_count": at_risk,
        "low_count": risk_bucket("Low"),
        "medium_count": risk_bucket("Medium"),
        "high_count": risk_bucket("High"),
        "critical_count": risk_bucket("Critical"),
        "total_planned_budget": total_planned_budget,
        "total_predicted_cost": total_predicted_cost,
        "total_overrun_amount": total_predicted_cost - total_planned_budget,
        "avg_overrun_pct": round(avg_overrun, 1),
        "avg_delay_days": round(avg_delay, 1),
    }
