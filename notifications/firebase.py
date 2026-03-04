import os
import json
import firebase_admin
from firebase_admin import credentials, messaging
from django.conf import settings

FIREBASE_SERVICE_ACCOUNT = os.getenv("FIREBASE_SERVICE_ACCOUNT")

if not FIREBASE_SERVICE_ACCOUNT:
    raise ValueError("FIREBASE_SERVICE_ACCOUNT environment variable not set.")

service_account_info = json.loads(FIREBASE_SERVICE_ACCOUNT)

cred = credentials.Certificate(service_account_info)

if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)


def send_push_notification(token, title, body, data=None):
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