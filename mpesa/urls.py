from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import mpesa_confirmation, mpesa_validation, MpesaTransactionViewSet

router = DefaultRouter()
router.register(r"transactions", MpesaTransactionViewSet, basename="mpesa-transactions")

urlpatterns = [
    path("confirmation/", mpesa_confirmation, name="mpesa-confirmation"),
    path("validation/", mpesa_validation, name="mpesa-validation"),
    path("", include(router.urls)),
]