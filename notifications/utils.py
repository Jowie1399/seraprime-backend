from firebase_admin import messaging
from .models import DeviceToken
from .firebase import initialize_firebase
import logging

logger = logging.getLogger(__name__)


def send_push_notification(token: str, title: str, body: str):
    """
    Send push notification using Firebase Admin SDK.
    Safe for production.
    """

    try:
        initialize_firebase()

        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            token=token,
        )

        response = messaging.send(message)
        return response

    except Exception as e:
        logger.error(f"Push notification failed: {str(e)}")


def notify_user_devices(user, title: str, body: str):
    devices = DeviceToken.objects.filter(user=user)

    for device in devices:
        send_push_notification(device.token, title, body)