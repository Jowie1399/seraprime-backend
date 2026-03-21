from .models import DeviceToken, Notification
from .expo import send_push_notification


def notify_user_devices(user, title, body, data=None):
    notification = Notification.objects.create(
        user=user,
        title=title,
        message=body,
    )

    tokens = user.device_tokens.all()

    for device in tokens:
        try:
            send_push_notification(
                token=device.token,
                title=title,
                body=body,
                data=data or {"notification_id": str(notification.id)},
            )
        except Exception:
            # optional: delete invalid token here if needed
            pass

    return notification