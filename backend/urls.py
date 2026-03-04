from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from properties.views import PropertyViewSet, UnitViewSet, TenantViewSet, LeaseViewSet
from billing.views import InvoiceViewSet, ReceiptViewSet
from properties.views import DashboardView
from mpesa.views import MpesaTransactionViewSet


router = DefaultRouter()
router.register(r"properties", PropertyViewSet, basename="property")
router.register(r"units", UnitViewSet, basename="unit")
router.register(r"tenants", TenantViewSet, basename="tenant")
router.register(r"leases", LeaseViewSet, basename="lease")
router.register(r"invoices", InvoiceViewSet, basename="invoice")
router.register(r"receipts", ReceiptViewSet, basename="receipt")
router.register(r"mpesa-transactions", MpesaTransactionViewSet, basename="mpesa-transactions")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("auth/", include("djoser.urls")),
    path("auth/", include("djoser.urls.jwt")),
    path("api/", include(router.urls)),
    path("api/dashboard/", DashboardView.as_view()),
    path("api/payments/", include("mpesa.urls")),
    path("api/notifications/", include("notifications.urls")),
    path('billing/', include('billing.urls')),


]
