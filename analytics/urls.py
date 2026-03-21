from django.urls import path
from .views import (
    property_list,
    rent_trend,
    receipts_trend,
    occupancy_stats,
    revenue_summary,
    dashboard_summary,
    invoice_receipt_comparison,
)

urlpatterns = [
    path("properties/", property_list),
    path("rent_trend/", rent_trend),
    path("receipts_trend/", receipts_trend),
    path("occupancy/", occupancy_stats),
    path("revenue/", revenue_summary),
    path("summary/", dashboard_summary),
    path("invoice_receipt_comparison/", invoice_receipt_comparison),
]