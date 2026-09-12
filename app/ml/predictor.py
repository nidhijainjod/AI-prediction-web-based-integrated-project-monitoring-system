"""Loads the trained models and turns a Project's current state into an
auto-generated prediction: final cost, schedule delay, a 0-100 risk score,
and a short list of plain-English reasons + recommendations driving that score.
"""
import os
from datetime import timedelta, date

import joblib

from app.ml import train as train_module
from app.ml.features import FEATURE_NAMES, FEATURE_META, features_for_project, feature_vector

_cost_model = None
_delay_model = None
_meta = None


def _ensure_models_loaded():
    global _cost_model, _delay_model, _meta
    if _cost_model is not None and _delay_model is not None:
        return
    if not (os.path.exists(train_module.COST_MODEL_PATH) and os.path.exists(train_module.DELAY_MODEL_PATH)):
        train_module.train_and_save()
    _cost_model = joblib.load(train_module.COST_MODEL_PATH)
    _delay_model = joblib.load(train_module.DELAY_MODEL_PATH)
    _meta = joblib.load(train_module.META_PATH)


def _risk_level_for(score, config=None):
    low_max = getattr(config, "RISK_LOW_MAX", 25) if config else 25
    med_max = getattr(config, "RISK_MEDIUM_MAX", 50) if config else 50
    high_max = getattr(config, "RISK_HIGH_MAX", 75) if config else 75
    if score <= low_max:
        return "Low"
    if score <= med_max:
        return "Medium"
    if score <= high_max:
        return "High"
    return "Critical"


# baseline "healthy" value for each feature, used to measure how much a
# project's current metric deviates from the neutral/expected value
_NEUTRAL_BASELINE = {
    "cost_ratio": 1.0,
    "schedule_ratio": 1.0,
    "blocked_ratio": 0.0,
    "overdue_ratio": 0.0,
    "task_completion_ratio": None,  # compares against percent_complete instead
}

_RECOMMENDATIONS = {
    "cost_ratio": "Review spend approvals and re-baseline the budget for remaining work; consider descoping non-critical items.",
    "schedule_ratio": "Compress the critical path — add resources to lagging tasks or renegotiate the delivery date now, before slip compounds.",
    "blocked_ratio": "Escalate blockers immediately; assign an owner to clear each blocked task within 48 hours.",
    "overdue_ratio": "Re-plan overdue tasks with realistic dates and confirm assignee capacity before committing to new deadlines.",
    "task_completion_ratio": "Break down remaining tasks into smaller units and check in more frequently to restore momentum.",
}


def _build_reasons_and_recommendations(features, importances):
    scored = []
    for name in FEATURE_NAMES:
        if name not in FEATURE_META:
            continue
        value = features[name]
        baseline = _NEUTRAL_BASELINE.get(name)
        if baseline is None:
            baseline = features["percent_complete"]
        deviation = value - baseline
        meta = FEATURE_META[name]
        worse_high = meta["worse_is"] == "high"
        bad_deviation = deviation if worse_high else -deviation
        importance = importances.get(name, 0.0)
        severity = max(bad_deviation, 0) * (0.5 + importance)
        scored.append((severity, name, value, bad_deviation, meta))

    scored.sort(key=lambda row: row[0], reverse=True)

    reasons = []
    recommendations = []
    for severity, name, value, bad_deviation, meta in scored[:3]:
        if bad_deviation > 0.05:
            if name in ("cost_ratio", "schedule_ratio"):
                pct = abs(value - 1.0) * 100
            else:
                pct = value * 100
            reasons.append(meta["reason_high"].format(pct=pct))
            recommendations.append(_RECOMMENDATIONS[name])
        else:
            reasons.append(meta["reason_low"].format(pct=value * 100))

    if not reasons:
        reasons = ["All tracked metrics are currently within healthy range for this stage of the project."]
    return reasons, recommendations


def predict_project(project, config=None):
    _ensure_models_loaded()

    features = features_for_project(project)
    X = [feature_vector(features)]

    overrun_pct = float(_cost_model.predict(X)[0])
    delay_days = float(_delay_model.predict(X)[0])

    avg_importance = {
        name: (_meta["feature_importances_cost"].get(name, 0) + _meta["feature_importances_delay"].get(name, 0)) / 2
        for name in FEATURE_NAMES
    }

    reasons, recommendations = _build_reasons_and_recommendations(features, avg_importance)

    predicted_final_cost = project.planned_budget * (1 + overrun_pct / 100.0)
    duration = project.planned_duration_days
    norm_cost = max(min(overrun_pct * 1.5, 100), -20)
    norm_delay = max(min((delay_days / duration) * 100 * 1.5, 100), -20)
    blocked_ratio = features["blocked_ratio"]
    overdue_ratio = features["overdue_ratio"]

    risk_score = (
        0.45 * max(norm_cost, 0)
        + 0.35 * max(norm_delay, 0)
        + 0.12 * blocked_ratio * 100
        + 0.08 * overdue_ratio * 100
    )
    risk_score = round(max(min(risk_score, 100), 0), 1)
    risk_level = _risk_level_for(risk_score, config)

    predicted_completion_date = (project.actual_start_date or project.planned_start_date) + timedelta(
        days=duration + max(delay_days, 0)
    )
    if project.status == "Completed":
        predicted_completion_date = project.actual_end_date or date.today()

    return {
        "predicted_final_cost": round(predicted_final_cost, 2),
        "predicted_overrun_pct": round(overrun_pct, 1),
        "predicted_delay_days": round(delay_days, 1),
        "predicted_completion_date": predicted_completion_date,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "reasons": reasons,
        "recommendations": recommendations,
        "features": features,
    }


def recompute_and_store(project, config=None, record_snapshot=True):
    from app.extensions import db
    from app.models import ProjectSnapshot
    from datetime import datetime

    result = predict_project(project, config=config)

    project.predicted_final_cost = result["predicted_final_cost"]
    project.predicted_overrun_pct = result["predicted_overrun_pct"]
    project.predicted_delay_days = result["predicted_delay_days"]
    project.predicted_completion_date = result["predicted_completion_date"]
    project.risk_score = result["risk_score"]
    project.risk_level = result["risk_level"]
    project.risk_reasons = result["reasons"]
    project.recommendations = result["recommendations"]
    project.last_predicted_at = datetime.utcnow()

    if record_snapshot:
        expected_pace = (project.percent_complete or 0) / 100.0
        snapshot = ProjectSnapshot(
            project_id=project.id,
            snapshot_date=date.today(),
            percent_complete=project.percent_complete or 0.0,
            actual_cost_to_date=project.actual_cost_to_date or 0.0,
            planned_cost_to_date=round(project.planned_budget * expected_pace, 2),
            risk_score=project.risk_score,
        )
        db.session.add(snapshot)

    return result
