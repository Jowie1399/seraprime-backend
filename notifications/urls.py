from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import NotificationViewSet, register_device_token

router = DefaultRouter()
router.register(r"", NotificationViewSet, basename="notifications")

urlpatterns = [
    path("register_device_token/", register_device_token),
    path("", include(router.urls)),
]