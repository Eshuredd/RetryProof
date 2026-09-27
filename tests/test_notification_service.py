import sqlite3

from samples.notification_service.app import create_app


def test_health(tmp_path):
    db_path = tmp_path / "notifications.db"
    app = create_app(str(db_path))
    client = app.test_client()

    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {
        "status": "ok",
        "service": "notification-service",
    }


def test_send_notification(tmp_path):
    db_path = tmp_path / "notifications.db"
    app = create_app(str(db_path))
    client = app.test_client()

    response = client.post(
        "/notifications/send",
        json={
            "message_id": "msg_001",
            "recipient": "demo@example.com",
            "message": "Hello",
        },
    )

    assert response.status_code == 201
    assert response.get_json() == {
        "job_id": 1,
        "message_id": "msg_001",
        "recipient": "demo@example.com",
    }

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT message_id, recipient, message FROM email_jobs"
        ).fetchone()

    assert row == ("msg_001", "demo@example.com", "Hello")


def test_send_notification_rejects_missing_fields(tmp_path):
    db_path = tmp_path / "notifications.db"
    app = create_app(str(db_path))
    client = app.test_client()

    response = client.post(
        "/notifications/send",
        json={"message_id": "msg_001"},
    )

    assert response.status_code == 400
    assert response.get_json() == {"error": "missing required field"}
