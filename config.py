import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Vercel (and similar serverless hosts) give the app a read-only deployment
# bundle plus a writable /tmp — set VERCEL automatically, so redirect any
# writable paths there instead of the repo itself.
IS_SERVERLESS = bool(os.environ.get("VERCEL"))
INSTANCE_DIR = "/tmp" if IS_SERVERLESS else os.path.join(BASE_DIR, "instance")
ML_ARTIFACTS_DIR = (
    "/tmp/ml_artifacts" if IS_SERVERLESS else os.path.join(BASE_DIR, "app", "ml", "artifacts")
)


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(INSTANCE_DIR, 'app.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = True

    # Risk thresholds (0-100 risk score)
    RISK_LOW_MAX = 25
    RISK_MEDIUM_MAX = 50
    RISK_HIGH_MAX = 75
