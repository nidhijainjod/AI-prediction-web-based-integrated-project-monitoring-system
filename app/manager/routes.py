from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user

from app.extensions import db
from app.models import Project, Task, User, ROLE_MANAGER
from app.manager.forms import ProjectForm, TaskForm
from app.utils import manager_required
from app.ml.predictor import recompute_and_store

manager_bp = Blueprint("manager", __name__, url_prefix="/manager")


def _owned_project_or_404(project_id):
    project = db.get_or_404(Project, project_id)
    if not current_user.is_admin and project.manager_id != current_user.id:
        abort(403)
    return project


@manager_bp.route("/projects")
@login_required
@manager_required
def projects():
    query = Project.query
    if not current_user.is_admin:
        query = query.filter_by(manager_id=current_user.id)
    my_projects = query.order_by(Project.updated_at.desc()).all()
    return render_template("manager/projects.html", projects=my_projects)


@manager_bp.route("/projects/new", methods=["GET", "POST"])
@login_required
@manager_required
def project_new():
    form = ProjectForm()
    if form.validate_on_submit():
        project = Project(manager_id=current_user.id)
        form.populate_obj(project)
        db.session.add(project)
        db.session.flush()
        recompute_and_store(project, record_snapshot=False)
        db.session.commit()
        flash(f"Project '{project.name}' created.", "success")
        return redirect(url_for("manager.project_detail", project_id=project.id))
    return render_template("manager/project_form.html", form=form, is_new=True, project=None)


@manager_bp.route("/projects/<int:project_id>")
@login_required
@manager_required
def project_detail(project_id):
    project = _owned_project_or_404(project_id)
    return render_template("manager/project_detail.html", project=project)


@manager_bp.route("/projects/<int:project_id>/edit", methods=["GET", "POST"])
@login_required
@manager_required
def project_edit(project_id):
    project = _owned_project_or_404(project_id)
    form = ProjectForm(obj=project)
    if form.validate_on_submit():
        form.populate_obj(project)
        recompute_and_store(project)
        db.session.commit()
        flash(f"Project '{project.name}' updated.", "success")
        return redirect(url_for("manager.project_detail", project_id=project.id))
    return render_template("manager/project_form.html", form=form, is_new=False, project=project)


@manager_bp.route("/projects/<int:project_id>/delete", methods=["POST"])
@login_required
@manager_required
def project_delete(project_id):
    project = _owned_project_or_404(project_id)
    name = project.name
    db.session.delete(project)
    db.session.commit()
    flash(f"Project '{name}' deleted.", "success")
    return redirect(url_for("manager.projects"))


@manager_bp.route("/projects/<int:project_id>/recalculate", methods=["POST"])
@login_required
@manager_required
def recalculate(project_id):
    project = _owned_project_or_404(project_id)
    recompute_and_store(project)
    db.session.commit()
    flash("AI prediction refreshed.", "success")
    return redirect(url_for("manager.project_detail", project_id=project.id))


def _assignable_users():
    return User.query.filter_by(is_active_flag=True).order_by(User.name).all()


@manager_bp.route("/projects/<int:project_id>/tasks/new", methods=["GET", "POST"])
@login_required
@manager_required
def task_new(project_id):
    project = _owned_project_or_404(project_id)
    form = TaskForm()
    form.assignee_id.choices = [(0, "Unassigned")] + [(u.id, u.name) for u in _assignable_users()]
    if form.validate_on_submit():
        task = Task()
        form.populate_obj(task)
        if form.assignee_id.data == 0:
            task.assignee_id = None
        project.tasks.append(task)
        project.recompute_rollups()
        recompute_and_store(project)
        db.session.commit()
        flash(f"Task '{task.name}' added.", "success")
        return redirect(url_for("manager.project_detail", project_id=project.id))
    return render_template("manager/task_form.html", form=form, is_new=True, project=project, task=None)


@manager_bp.route("/projects/<int:project_id>/tasks/<int:task_id>/edit", methods=["GET", "POST"])
@login_required
@manager_required
def task_edit(project_id, task_id):
    project = _owned_project_or_404(project_id)
    task = Task.query.filter_by(id=task_id, project_id=project.id).first_or_404()
    form = TaskForm(obj=task)
    form.assignee_id.choices = [(0, "Unassigned")] + [(u.id, u.name) for u in _assignable_users()]
    if request.method == "GET":
        form.assignee_id.data = task.assignee_id or 0

    if form.validate_on_submit():
        form.populate_obj(task)
        if form.assignee_id.data == 0:
            task.assignee_id = None
        project.recompute_rollups()
        recompute_and_store(project)
        db.session.commit()
        flash(f"Task '{task.name}' updated.", "success")
        return redirect(url_for("manager.project_detail", project_id=project.id))
    return render_template("manager/task_form.html", form=form, is_new=False, project=project, task=task)


@manager_bp.route("/projects/<int:project_id>/tasks/<int:task_id>/delete", methods=["POST"])
@login_required
@manager_required
def task_delete(project_id, task_id):
    project = _owned_project_or_404(project_id)
    task = Task.query.filter_by(id=task_id, project_id=project.id).first_or_404()
    project.tasks.remove(task)
    project.recompute_rollups()
    recompute_and_store(project)
    db.session.commit()
    flash("Task deleted.", "success")
    return redirect(url_for("manager.project_detail", project_id=project.id))
