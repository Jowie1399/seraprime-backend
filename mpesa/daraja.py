import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime, timedelta
from django.conf import settings


# Environment-based URLs
if settings.MPESA_ENVIRONMENT == "production":
    BASE_URL = "https://api.safaricom.co.ke"
else:
    BASE_URL = "https://sandbox.safaricom.co.ke"


OAUTH_URL = f"{BASE_URL}/oauth/v1/generate?grant_type=client_credentials"
C2B_REGISTER_URL = f"{BASE_URL}/mpesa/c2b/v1/registerurl"


# Simple in-memory token cache
_access_token = None
_token_expiry = datetime.now()


def get_access_token():
    global _access_token, _token_expiry

    if _access_token and _token_expiry > datetime.now():
        return _access_token

    response = requests.get(
        OAUTH_URL,
        auth=HTTPBasicAuth(
            settings.MPESA_CONSUMER_KEY,
            settings.MPESA_CONSUMER_SECRET
        )
    )

    response.raise_for_status()
    data = response.json()

    _access_token = data["access_token"]
    _token_expiry = datetime.now() + timedelta(
        seconds=int(data.get("expires_in", 3599)) - 30
    )

    return _access_token


def register_c2b_urls():
    """
    Register confirmation and validation URLs with Daraja.
    Run once when setting up sandbox or production.
    """
    access_token = get_access_token()

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    payload = {
        "ShortCode": settings.MPESA_SHORTCODE,
        "ResponseType": "Completed",
        "ConfirmationURL": settings.MPESA_CONFIRMATION_URL,
        "ValidationURL": settings.MPESA_VALIDATION_URL
    }

    response = requests.post(C2B_REGISTER_URL, json=payload, headers=headers)
    print(response.text)
    return response.json()

    