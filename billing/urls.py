from django.urls import path
from .views import trigger_monthly_invoices, trigger_past_due_notifications

urlpatterns = [
    path('demo/generate-invoices/', trigger_monthly_invoices),
    path('demo/past-due/', trigger_past_due_notifications),
]