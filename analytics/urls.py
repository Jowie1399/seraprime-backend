# analytics/urls.py
from django.urls import path
from .views import rent_trend, occupancy_stats, revenue_summary

urlpatterns = [
    path("rent_trend/", rent_trend),
    path("occupancy/", occupancy_stats),
    path("revenue/", revenue_summary),
]