# RetryProof — Milestone 1

**RetryProof** is a developer tool for the IBM Bob 2.0 Hackathon that reproduces
retry-related backend failures, helps IBM Bob repair the responsible application
code, and independently verifies whether the repair actually works.

---

## Project layout

```
RetryProof/
├── app/
│   ├── database.py          # SQLite helpers
│   └── main.py              # FastAPI app
├── verifier/
│   └── verify_idempotency.py  # standalone verifier script
├── tests/
│   ├── test_health.py
│   ├── test_shipments.py    # ← one test intentionally fails (see below)
│   └── test_verifier.py     # ← one test intentionally fails (see below)
├── evidence/                # JSON evidence files land here
├── bob_sessions/            # IBM Bob session artifacts
├── requirements.txt
└── README.md
```

---

## Quick start (PowerShell)

```powershell
# 1. Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the development server
uvicorn app.main:app --reload

# 4. (separate terminal) Run the test suite
pytest -v

# 5. Run the verifier
python -m verifier.verify_idempotency
```

---

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET    | `/health` | Health check — returns `{"status": "ok"}` |
| POST   | `/events/order-confirmed` | Process an order-confirmed event |

### Example request

```json
{
  "event_id": "evt_1001",
  "event_type": "order.confirmed",
  "order_id": "order_1001"
}
```

### Example response (201)

```json
{
  "shipment_id": 1,
  "event_id": "evt_1001",
  "order_id": "order_1001"
}
```

---

## Intentional bug (Milestone 1)

The `/events/order-confirmed` handler performs an **unconditional INSERT**
with no idempotency guard.  Delivering the same `event_id` multiple times
creates multiple shipment rows in the database.

This bug is deliberate — it is the failure mode that RetryProof is designed
to expose and repair.

---

## Verifier

`verifier/verify_idempotency.py` is a standalone script that:

1. Creates a fresh temporary SQLite database.
2. Sends the same event exactly **5 times**.
3. Queries the persisted shipment records.
4. Asserts exactly **1 shipment** exists.
5. Prints a human-readable report and saves JSON evidence to
   `evidence/idempotency_report.json`.
6. Exits with code `1` when the contract fails (Milestone 1 → always fails).

---

## Intentionally failing tests

| Test | File | Why it fails |
|------|------|-------------|
| `test_duplicate_event_creates_only_one_shipment` | `tests/test_shipments.py` | Asserts count == 1; buggy handler inserts 5 rows |
| `test_verifier_detects_duplicate_shipments` | `tests/test_verifier.py` | Same assertion via the verifier helper path |

Do **not** weaken these assertions.  They define the acceptance contract that
must pass after the bug is fixed.

---

## Evidence

After running the verifier, the JSON evidence file is at:

```
evidence/idempotency_report.json
```

---

## Security notes

- No credentials, API keys, or secrets anywhere in this repository.
- No external API calls.
- No frontend.
- Database files (`*.db`) are git-ignored.
