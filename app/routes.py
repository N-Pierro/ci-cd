from flask import Blueprint, current_app, jsonify, request
from sqlalchemy import text

from .models import Task, db

bp = Blueprint("api", __name__)

MAX_TITLE_LEN = 120


def _validate_title(value):
    if not isinstance(value, str):
        return "title must be a string"
    value = value.strip()
    if not value or len(value) > MAX_TITLE_LEN:
        return f"title must be 1-{MAX_TITLE_LEN} characters"
    return None


# ---- Probes (used by Docker HEALTHCHECK and Kubernetes) ---------------------
@bp.get("/healthz")
def healthz():
    """Liveness: the process is up."""
    return jsonify(status="ok")


@bp.get("/readyz")
def readyz():
    """Readiness: dependencies (database) are reachable."""
    try:
        db.session.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001 - any DB failure means "not ready"
        current_app.logger.exception("readiness check failed")
        return jsonify(status="unavailable"), 503
    return jsonify(status="ready")


# ---- Tasks API ----------------------------------------------------------------
@bp.get("/api/v1/tasks")
def list_tasks():
    tasks = Task.query.order_by(Task.id).all()
    return jsonify([t.to_dict() for t in tasks])


@bp.post("/api/v1/tasks")
def create_task():
    data = request.get_json(silent=True) or {}
    error = _validate_title(data.get("title"))
    if error:
        return jsonify(error=error), 400
    task = Task(title=data["title"].strip())
    db.session.add(task)
    db.session.commit()
    return jsonify(task.to_dict()), 201


@bp.get("/api/v1/tasks/<int:task_id>")
def get_task(task_id):
    return jsonify(db.get_or_404(Task, task_id).to_dict())


@bp.patch("/api/v1/tasks/<int:task_id>")
def update_task(task_id):
    task = db.get_or_404(Task, task_id)
    data = request.get_json(silent=True) or {}
    if "title" in data:
        error = _validate_title(data["title"])
        if error:
            return jsonify(error=error), 400
        task.title = data["title"].strip()
    if "done" in data:
        if not isinstance(data["done"], bool):
            return jsonify(error="done must be a boolean"), 400
        task.done = data["done"]
    db.session.commit()
    return jsonify(task.to_dict())


@bp.delete("/api/v1/tasks/<int:task_id>")
def delete_task(task_id):
    task = db.get_or_404(Task, task_id)
    db.session.delete(task)
    db.session.commit()
    return "", 204
