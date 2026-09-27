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


def test_send_notification_idempotent_retries(tmp_path):
    """Five POSTs with the same message_id must produce exactly one DB row
    and return 201 with the same job_id every time."""
    db_path = tmp_path / "notifications.db"
    app = create_app(str(db_path))
    client = app.test_client()

    payload = {
        "message_id": "msg_rp_001",
        "recipient": "demo@example.com",
        "message": "Your report is ready",
    }

    responses = [
        client.post("/notifications/send", json=payload) for _ in range(5)
    ]

    # All five responses must be 201.
    for resp in responses:
        assert resp.status_code == 201

    # All five responses must carry the same job_id.
    job_ids = [resp.get_json()["job_id"] for resp in responses]
    assert len(set(job_ids)) == 1, f"Expected one unique job_id, got: {job_ids}"

    # Exactly one row must exist in the database.
    with sqlite3.connect(db_path) as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM email_jobs WHERE message_id = ?",
            ("msg_rp_001",),
        ).fetchone()[0]

    assert count == 1


def test_distinct_message_id_creates_own_row(tmp_path):
    """A different message_id must still produce its own independent row."""
    db_path = tmp_path / "notifications.db"
    app = create_app(str(db_path))
    client = app.test_client()

    for msg_id in ("msg_A", "msg_B"):
        resp = client.post(
            "/notifications/send",
            json={
                "message_id": msg_id,
                "recipient": "demo@example.com",
                "message": f"Message {msg_id}",
            },
        )
        assert resp.status_code == 201

    with sqlite3.connect(db_path) as conn:
        count = conn.execute("SELECT COUNT(*) FROM email_jobs").fetchone()[0]

    assert count == 2


def test_init_db_deduplicates_legacy_rows(tmp_path):
    """init_db must purge duplicate message_id rows from a legacy database
    (keeping the earliest id) and then successfully create the unique index.
    Without this the unique index would fail and INSERT OR IGNORE would not
    provide idempotency."""
    from samples.notification_service.database import get_db, init_db

    db_path = str(tmp_path / "legacy.db")

    # Seed a legacy schema WITHOUT the unique constraint and insert duplicates.
    with get_db(db_path) as seed:
        seed.execute(
            """
            CREATE TABLE email_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id TEXT NOT NULL,
                recipient TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        seed.executemany(
            "INSERT INTO email_jobs (message_id, recipient, message) VALUES (?, ?, ?)",
            [
                ("dup_msg", "a@example.com", "first"),
                ("dup_msg", "a@example.com", "second"),
                ("dup_msg", "a@example.com", "third"),
                ("unique_msg", "b@example.com", "only"),
            ],
        )
        seed.commit()

    # init_db should deduplicate and create the index without raising.
    init_db(db_path)

    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT id, message_id FROM email_jobs ORDER BY id"
        ).fetchall()

    # Only the first occurrence of dup_msg survives; unique_msg is untouched.
    assert len(rows) == 2
    assert rows[0][1] == "dup_msg"
    assert rows[1][1] == "unique_msg"

    # The unique index must now exist.
    idx = sqlite3.connect(db_path).execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_email_jobs_message_id'"
    ).fetchone()
    assert idx is not None, "unique index was not created after deduplication"
