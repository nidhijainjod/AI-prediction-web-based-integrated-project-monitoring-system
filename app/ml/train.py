"""Trains the cost/schedule overrun predictors on a synthetic historical dataset.

There is no real "completed projects" history to learn from yet, so this
generates a large synthetic population of plausible project *stages* (a
snapshot of a project partway through its life) together with a simulated
"eventual outcome" (final cost overrun % and final schedule delay in days).
The simulation encodes realistic project-management dynamics (e.g. spend
running ahead of pace tends to compound into overrun; blocked/overdue tasks
tend to compound into delay) plus noise, so the regressors learn genuine,
explainable relationships rather than a hand-written formula. Once real
historical project outcomes exist, swap this generator for a query against
completed projects and retrain the same way.
"""
import os
import numpy as np
from sklearn.ensemble import RandomForestRegressor
import joblib

from app.ml.features import FEATURE_NAMES, CATEGORIES
from config import ML_ARTIFACTS_DIR

ARTIFACTS_DIR = ML_ARTIFACTS_DIR
COST_MODEL_PATH = os.path.join(ARTIFACTS_DIR, "cost_overrun_model.joblib")
DELAY_MODEL_PATH = os.path.join(ARTIFACTS_DIR, "delay_model.joblib")
META_PATH = os.path.join(ARTIFACTS_DIR, "meta.joblib")


def _simulate_dataset(n_samples=4000, seed=42):
    rng = np.random.default_rng(seed)

    percent_complete = rng.uniform(0.03, 0.99, n_samples)
    # cost/schedule "pace ratios": 1.0 == exactly on pace, >1 == running hot
    cost_ratio = np.clip(rng.normal(1.0, 0.28, n_samples), 0.4, 2.8)
    schedule_ratio = np.clip(rng.normal(1.0, 0.25, n_samples), 0.4, 2.6)

    task_completion_ratio = np.clip(percent_complete + rng.normal(0, 0.08, n_samples), 0, 1)
    blocked_ratio = np.clip(rng.beta(1.2, 9.0, n_samples), 0, 0.8)
    overdue_ratio = np.clip(
        rng.beta(1.3, 7.0, n_samples) + (schedule_ratio - 1.0).clip(min=0) * 0.3, 0, 0.9
    )

    team_size = rng.integers(2, 25, n_samples)
    priority_encoded = rng.integers(1, 4, n_samples)
    category_encoded = rng.integers(0, len(CATEGORIES), n_samples)

    noise_cost = rng.normal(0, 8, n_samples)
    noise_delay = rng.normal(0, 6, n_samples)

    # --- simulated ground truth relationships ---
    final_overrun_pct = (
        (cost_ratio - 1.0) * 95
        + blocked_ratio * 35
        + overdue_ratio * 22
        - (task_completion_ratio - percent_complete) * 15
        + noise_cost
    )
    final_overrun_pct = np.clip(final_overrun_pct, -15, 140)

    planned_duration_proxy = 60 + team_size * 4  # bigger teams -> typically longer projects
    final_delay_days = (
        (schedule_ratio - 1.0) * planned_duration_proxy * 0.9
        + overdue_ratio * planned_duration_proxy * 0.35
        + blocked_ratio * planned_duration_proxy * 0.25
        + noise_delay
    )
    final_delay_days = np.clip(final_delay_days, -20, planned_duration_proxy * 1.6)

    X = np.column_stack(
        [
            percent_complete,
            cost_ratio,
            schedule_ratio,
            task_completion_ratio,
            blocked_ratio,
            overdue_ratio,
            team_size,
            priority_encoded,
            category_encoded,
        ]
    )
    assert X.shape[1] == len(FEATURE_NAMES)
    return X, final_overrun_pct, final_delay_days


def train_and_save(n_samples=4000, seed=42):
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)
    X, y_overrun, y_delay = _simulate_dataset(n_samples=n_samples, seed=seed)

    cost_model = RandomForestRegressor(
        n_estimators=250, max_depth=7, min_samples_leaf=4, random_state=seed
    )
    cost_model.fit(X, y_overrun)

    delay_model = RandomForestRegressor(
        n_estimators=250, max_depth=7, min_samples_leaf=4, random_state=seed
    )
    delay_model.fit(X, y_delay)

    joblib.dump(cost_model, COST_MODEL_PATH)
    joblib.dump(delay_model, DELAY_MODEL_PATH)
    joblib.dump(
        {
            "feature_names": FEATURE_NAMES,
            "feature_importances_cost": dict(zip(FEATURE_NAMES, cost_model.feature_importances_)),
            "feature_importances_delay": dict(zip(FEATURE_NAMES, delay_model.feature_importances_)),
        },
        META_PATH,
    )
    return cost_model, delay_model


if __name__ == "__main__":
    train_and_save()
    print("Trained and saved models to", ARTIFACTS_DIR)
