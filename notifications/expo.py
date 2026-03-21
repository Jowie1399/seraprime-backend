import requests

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"


def send_push_notification(token, title, body, data=None):
    payload = {
        "to": token,
        "title": title,
        "body": body,
        "sound": "default",
        "data": data or {},
    }

    response = requests.post(
        EXPO_PUSH_URL,
        json=payload,
        headers={
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate",
            "Content-Type": "application/json",
        },
        timeout=15,
    )

    response.raise_for_status()
    return response.json()