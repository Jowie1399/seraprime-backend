from .models import DeviceToken
from .firebase import send_push_notification


def notify_user_devices(user, title, body):
    tokens = user.device_tokens.all()

    for device in tokens:
        try:
            send_push_notification(
                token=device.token,
                title=title,
                body=body
            )
        except Exception:
            pass