from __future__ import annotations

import os
from pathlib import Path

from flask import Flask, jsonify
from dotenv import load_dotenv

from .db_common import DatabaseUnavailable
from .routes import api


def create_app(test_config: dict | None = None) -> Flask:
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    app = Flask(__name__)
    app.config.from_mapping(
        MAX_CONTENT_LENGTH=int(os.getenv("MAX_UPLOAD_MB", "25")) * 1024 * 1024,
        DATABASE_ENGINE=os.getenv("DATABASE_ENGINE", "sqlserver").strip().lower(),
        SQLSERVER_CONNECTION_STRING=os.getenv("SQLSERVER_CONNECTION_STRING", ""),
        SQLITE_DATABASE_PATH=os.getenv(
            "SQLITE_DATABASE_PATH",
            str(Path(__file__).resolve().parents[1] / "data" / "invoice_ocr.db"),
        ),
        AUTO_INIT_DB=os.getenv("AUTO_INIT_DB", "true").lower() in {"1", "true", "yes"},
    )
    if test_config:
        app.config.update(test_config)

    if app.config["DATABASE_ENGINE"] == "sqlite":
        from .sqlite_db import SQLiteInvoiceRepository
        repository = SQLiteInvoiceRepository(app.config["SQLITE_DATABASE_PATH"])
    elif app.config["DATABASE_ENGINE"] == "sqlserver":
        from .db import InvoiceRepository
        repository = InvoiceRepository(app.config["SQLSERVER_CONNECTION_STRING"])
    else:
        raise ValueError("DATABASE_ENGINE phải là 'sqlite' hoặc 'sqlserver'.")
    app.extensions["invoice_repository"] = repository
    if app.config["AUTO_INIT_DB"] and repository.configured:
        repository.initialize()

    app.register_blueprint(api, url_prefix="/api")
    from .parse_jobs import ParseJobs
    app.extensions["parse_jobs"] = ParseJobs(os.getenv(
        "PARSE_JOBS_PATH", str(Path(app.config["SQLITE_DATABASE_PATH"]).parent / "parse_jobs.db")
    ))

    @app.after_request
    def add_cors_headers(response):
        response.headers["Access-Control-Allow-Origin"] = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        response.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,DELETE,OPTIONS"
        return response

    @app.errorhandler(DatabaseUnavailable)
    def database_unavailable(error):
        return jsonify({"error": str(error), "code": "database_unavailable"}), 503

    @app.errorhandler(413)
    def too_large(_error):
        return jsonify({"error": "File vượt quá dung lượng cho phép."}), 413

    return app
