from __future__ import annotations

import os

from flask import Flask, jsonify, request

from samples.notification_service.database import get_db, init_db


def create_app(database_path: str | None = None) -> Flask:
    app = Flask(__name__)

    app.config["DATABASE_PATH"] = (
        database_path
        or os.getenv("NOTIFICATION_DB_PATH", "notification_demo.db")
    )

    init_db(app.config["DATABASE_PATH"])

    @app.get("/health")
    def health():
        return jsonify(
            {
                "status": "ok",
                "service": "notification-service",
            }
        )

    @app.post("/notifications/send")
    def send_notification():
        body = request.get_json(silent=True) or {}

        required = ("message_id", "recipient", "message")

        if any(field not in body for field in required):
            return jsonify({"error": "missing required field"}), 400

        conn = get_db(app.config["DATABASE_PATH"])

        try:
            # INSERT OR IGNORE silently skips duplicate message_id values,
            # making the endpoint idempotent against retries.
            conn.execute(
                """
                INSERT OR IGNORE INTO email_jobs (
                    message_id,
                    recipient,
                    message
                )
                VALUES (?, ?, ?)
                """,
                (
                    body["message_id"],
                    body["recipient"],
                    body["message"],
                ),
            )

            conn.commit()

            # Fetch the canonical row whether it was just inserted or already
            # existed from an earlier delivery.
            row = conn.execute(
                "SELECT id FROM email_jobs WHERE message_id = ?",
                (body["message_id"],),
            ).fetchone()
            job_id = row["id"]

        finally:
            conn.close()

        return (
            jsonify(
                {
                    "job_id": job_id,
                    "message_id": body["message_id"],
                    "recipient": body["recipient"],
                }
            ),
            201,
        )

    return app


app = create_app()


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=8001,
        debug=False,
    )