from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from sqlalchemy import func

from app.extensions import db
from app.models import User, Project, Task, ROLE_ADMIN, ROLE_MANAGER
from app.admin.forms import UserForm
from app.utils import admin_required, portfolio_summary
from app.ml.predictor import recompute_and_store

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/dashboard")
@login_required
@admin_required
def dashboard():
    projects = Project.query.order_by(Project.risk_score.desc().nullslast()).all()
    summary = portfolio_summary(projects)
    return render_template("admin/dashboard.html", projects=projects, summary=summary)


@admin_bp.route("/projects/<int:project_id>")
@login_required
@admin_required
def project_detail(project_id):
    project = db.get_or_404(Project, project_id)
    snapshots = project.snapshots
    return render_template("admin/project_detail.html", project=project, snapshots=snapshots)


@admin_bp.route("/projects/<int:project_id>/recalculate", methods=["POST"])
@login_required
@admin_required
def recalculate(project_id):
    project = db.get_or_404(Project, project_id)
    recompute_and_store(project)
    db.session.commit()
    flash(f"AI prediction refreshed for '{project.name}'.", "success")
    return redirect(request.referrer or url_for("admin.project_detail", project_id=project.id))


@admin_bp.route("/users")
@login_required
@admin_required
def users():
    all_users = User.query.order_by(User.created_at.desc()).all()
    return render_template("admin/users.html", users=all_users)


@admin_bp.route("/users/new", methods=["GET", "POST"])
@login_required
@admin_required
def user_new():
    form = UserForm()
    if form.validate_on_submit():
        if User.query.filter_by(email=form.email.data.lower().strip()).first():
            flash("A user with that email already exists.", "danger")
        elif not form.password.data:
            flash("Password is required for a new user.", "danger")
        else:
            user = User(
                name=form.name.data.strip(),
                email=form.email.data.lower().strip(),
                role=form.role.data,
                is_active_flag=form.is_active_flag.data,
            )
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            flash(f"User '{user.name}' created.", "success")
            return redirect(url_for("admin.users"))
    return render_template("admin/user_form.html", form=form, is_new=True, user=None)


@admin_bp.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def user_edit(user_id):
    user = db.get_or_404(User, user_id)
    form = UserForm(obj=user)
    if request.method == "GET":
        form.password.data = ""

    if form.validate_on_submit():
        existing = User.query.filter_by(email=form.email.data.lower().strip()).first()
        if existing and existing.id != user.id:
            flash("Another user already uses that email.", "danger")
        else:
            user.name = form.name.data.strip()
            user.email = form.email.data.lower().strip()
            user.role = form.role.data
            user.is_active_flag = form.is_active_flag.data
            if form.password.data:
                user.set_password(form.password.data)
            db.session.commit()
            flash(f"User '{user.name}' updated.", "success")
            return redirect(url_for("admin.users"))

    return render_template("admin/user_form.html", form=form, is_new=False, user=user)


@admin_bp.route("/users/<int:user_id>/delete", methods=["POST"])
@login_required
@admin_required
def user_delete(user_id):
    user = db.get_or_404(User, user_id)
    if user.id == current_user.id:
        flash("You cannot delete your own account.", "danger")
        return redirect(url_for("admin.users"))

    if user.projects:
        user.is_active_flag = False
        db.session.commit()
        flash(f"'{user.name}' manages existing projects, so the account was deactivated instead of deleted.", "warning")
    else:
        db.session.delete(user)
        db.session.commit()
        flash(f"User '{user.name}' deleted.", "success")
    return redirect(url_for("admin.users"))
