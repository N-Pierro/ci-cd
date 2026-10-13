import logging

from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException

from .config import Config
from .models import db
from .routes import bp


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)

    logging.basicConfig(
        level=app.config["LOG_LEVEL"],
        format='{"time":"%(asctime)s","level":"%(levelname)s","msg":"%(message)s"}',
    )

    db.init_app(app)
    with app.app_context():
        db.create_all()
    app.register_blueprint(bp)

    @app.after_request
    def security_headers(resp):
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["Cache-Control"] = "no-store"
        resp.headers["Content-Security-Policy"] = "default-src 'none'"
        return resp

    @app.errorhandler(HTTPException)
    def http_error(err):
        return jsonify(error=err.name), err.code

    @app.errorhandler(Exception)
    def unhandled(err):
        app.logger.exception("unhandled error")  # details go to logs only
        return jsonify(error="Internal Server Error"), 500

    return app
