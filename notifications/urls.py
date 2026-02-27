from django.urls import path
from .views import register_device_token

urlpatterns = [
    path("register-device/", register_device_token),
]