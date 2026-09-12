from flask import Blueprint, jsonify, request, abort
from flask_login import login_required, current_user

from app.extensions import db
from app.models import Task, Project
from app.ml.predictor import recompute_and_store

api_bp = Blueprint("api", __name__, url_prefix="/api")


def _project_prediction_payload(project):
    return {
        "project_id": project.id,
        "percent_complete": project.percent_complete,
        "actual_cost_to_date": project.actual_cost_to_date,
        "predicted_final_cost": project.predicted_final_cost,
        "predicted_overrun_pct": project.predicted_overrun_pct,
        "predicted_delay_days": project.predicted_delay_days,
        "predicted_completion_date": (
            project.predicted_completion_date.isoformat() if project.predicted_completion_date else None
        ),
        "risk_score": project.risk_score,
        "risk_level": project.risk_level,
        "reasons": project.risk_reasons,
        "recommendations": project.recommendations,
    }


def _can_access_project(project):
    return current_user.is_admin or project.manager_id == current_user.id


@api_bp.route("/tasks/<int:task_id>/quick-update", methods=["POST"])
@login_required
def task_quick_update(task_id):
    task = db.get_or_404(Task, task_id)
    project = task.project
    # Administrators have read-only oversight; only the owning manager may edit tasks.
    if current_user.is_admin or project.manager_id != current_user.id:
        abort(403)

    payload = request.get_json(silent=True) or {}
    if "status" in payload:
        task.status = payload["status"]
        if task.status == "Completed":
            task.percent_complete = 100
    if "percent_complete" in payload:
        try:
            task.percent_complete = max(0, min(100, float(payload["percent_complete"])))
        except (TypeError, ValueError):
            abort(400)

    project.recompute_rollups()
    result = recompute_and_store(project)
    db.session.commit()

    return jsonify(
        {
            "task": {
                "id": task.id,
                "status": task.status,
                "percent_complete": task.percent_complete,
            },
            "project": _project_prediction_payload(project),
        }
    )


@api_bp.route("/projects/<int:project_id>/recalculate", methods=["POST"])
@login_required
def recalculate_prediction(project_id):
    project = db.get_or_404(Project, project_id)
    if not _can_access_project(project):
        abort(403)
    recompute_and_store(project)
    db.session.commit()
    return jsonify(_project_prediction_payload(project))


@api_bp.route("/projects/<int:project_id>/prediction")
@login_required
def get_prediction(project_id):
    project = db.get_or_404(Project, project_id)
    if not _can_access_project(project):
        abort(403)
    return jsonify(_project_prediction_payload(project))
