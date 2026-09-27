"""Start the notification service with waitress. Run in background."""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from waitress import serve
from samples.notification_service.app import create_app

app = create_app("notification_demo.db")
print("Serving notification-service on http://127.0.0.1:8001", flush=True)
serve(app, host="127.0.0.1", port=8001, threads=4)
