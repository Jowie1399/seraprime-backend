import os
import json
import firebase_admin
from firebase_admin import credentials, messaging

FIREBASE_SERVICE_ACCOUNT = os.getenv("FIREBASE_SERVICE_ACCOUNT")

firebase_app = None

if FIREBASE_SERVICE_ACCOUNT:
    service_account_info = json.loads(FIREBASE_SERVICE_ACCOUNT)
    cred = credentials.Certificate(service_account_info)

    if not firebase_admin._apps:
        firebase_app = firebase_admin.initialize_app(cred)
else:
    # Development mode — Firebase disabled
    print("⚠ Firebase not configured. Push notifications disabled.")


def send_push_notification(token, title, body, data=None):
    if not FIREBASE_SERVICE_ACCOUNT:
        print("⚠ Push skipped (Firebase not configured).")
        return None

    message = messaging.Message(
        notification=messaging.Notification(
            title=title,
            body=body,
        ),
        token=token,
        data=data or {},
    )

    response = messaging.send(message)
    return response