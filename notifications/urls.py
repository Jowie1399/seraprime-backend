from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import NotificationViewSet, register_device_token, unregister_device_token

router = DefaultRouter()
router.register(r"", NotificationViewSet, basename="notifications")

urlpatterns = [
    path("register_device_token/", register_device_token, name="register_device_token"),
    path("unregister_device_token/", unregister_device_token, name="unregister_device_token"),
    path("", include(router.urls)),
]