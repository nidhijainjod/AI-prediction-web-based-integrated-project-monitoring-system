from flask import Flask, render_template, redirect, url_for
from flask_login import current_user

from config import Config, IS_SERVERLESS
from app.extensions import db, login_manager, csrf


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    if IS_SERVERLESS:
        with app.app_context():
            from app.seed_data import ensure_demo_data

            ensure_demo_data()

    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to access this page."
    login_manager.login_message_category = "warning"

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    from app.auth.routes import auth_bp
    from app.admin.routes import admin_bp
    from app.manager.routes import manager_bp
    from app.api.routes import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(manager_bp)
    app.register_blueprint(api_bp)

    def _render_landing_page():
        from app.models import Project, Task
        from app.utils import portfolio_summary

        projects = Project.query.order_by(Project.risk_score.desc().nullslast()).all()
        summary = portfolio_summary(projects)

        category_counts = {}
        for p in projects:
            category_counts[p.category] = category_counts.get(p.category, 0) + 1
        top_categories = sorted(category_counts.items(), key=lambda kv: kv[1], reverse=True)[:5]
        max_category_count = max((c for _, c in top_categories), default=1)

        top_risk_projects = [p for p in projects if p.risk_level in ("High", "Critical")][:4]
        spotlight_project = projects[0] if projects and projects[0].risk_reasons else None

        return render_template(
            "index.html",
            summary=summary,
            total_tasks=Task.query.count(),
            top_categories=top_categories,
            max_category_count=max_category_count,
            top_risk_projects=top_risk_projects,
            spotlight_project=spotlight_project,
        )

    @app.route("/")
    def index():
        if current_user.is_authenticated:
            if current_user.is_admin:
                return redirect(url_for("admin.dashboard"))
            return redirect(url_for("manager.projects"))
        return _render_landing_page()

    @app.route("/landing")
    def landing_preview():
        """Always shows the marketing landing page, even while logged in — for previewing it."""
        return _render_landing_page()

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.template_filter("currency")
    def currency_filter(value):
        try:
            return f"${value:,.0f}"
        except (TypeError, ValueError):
            return "$0"

    @app.template_filter("risk_badge")
    def risk_badge_filter(level):
        mapping = {
            "Low": "success",
            "Medium": "warning",
            "High": "danger",
            "Critical": "dark",
        }
        return mapping.get(level, "secondary")

    return app
