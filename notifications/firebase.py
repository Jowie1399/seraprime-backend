import firebase_admin
from firebase_admin import credentials
from django.conf import settings
import os

firebase_app = None


def initialize_firebase():
    global firebase_app

    if firebase_app:
        return firebase_app

    cred_path = os.path.join(settings.BASE_DIR, settings.FIREBASE_CREDENTIALS_PATH)

    cred = credentials.Certificate(cred_path)
    firebase_app = firebase_admin.initialize_app(cred)

    return firebase_app