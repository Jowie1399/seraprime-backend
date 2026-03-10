from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    PropertyViewSet,
    UnitViewSet,
    TenantViewSet,
    LeaseViewSet,
    DashboardView
)

router = DefaultRouter()
router.register(r"properties", PropertyViewSet, basename="properties")
router.register(r"units", UnitViewSet, basename="units")
router.register(r"tenants", TenantViewSet, basename="tenants")
router.register(r"leases", LeaseViewSet, basename="leases")

urlpatterns = [
    path("", include(router.urls)),

    # Dashboard endpoint
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
]