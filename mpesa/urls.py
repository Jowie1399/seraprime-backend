from django.urls import path
from .views import mpesa_confirmation, mpesa_validation

urlpatterns = [
    path("confirmation/", mpesa_confirmation, name="mpesa-confirmation"),
    path("validation/", mpesa_validation, name="mpesa-validation"),
]