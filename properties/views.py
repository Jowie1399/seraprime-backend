from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import Property, Unit, Tenant, Lease
from .serializers import (
    PropertySerializer,
    UnitSerializer,
    TenantSerializer,
    LeaseSerializer,
)


class PropertyViewSet(viewsets.ModelViewSet):
    serializer_class = PropertySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Property.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class UnitViewSet(viewsets.ModelViewSet):
    serializer_class = UnitSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["property"]

    def get_queryset(self):
        return Unit.objects.filter(property__owner=self.request.user)


class TenantViewSet(viewsets.ModelViewSet):
    serializer_class = TenantSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["property"]

    def get_queryset(self):
        return Tenant.objects.filter(property__owner=self.request.user)

    @action(detail=True, methods=["get"])
    def statement(self, request, pk=None):
        tenant = self.get_object()
        leases = tenant.leases.all()
        invoices = []

        for lease in leases:
            for invoice in lease.invoices.all():
                invoices.append({
                    "invoice_id": invoice.id,
                    "amount": invoice.amount,
                    "due_date": invoice.due_date,
                    "status": invoice.status,
                    "total_paid": invoice.total_paid(),
                    "balance": invoice.balance(),
                })

        return Response({
            "tenant": tenant.full_name,
            "wallet_balance": tenant.wallet_balance,
            "invoices": invoices
        })

    @action(detail=True, methods=["get"])
    def arrears(self, request, pk=None):
        tenant = self.get_object()
        return Response({
            "tenant": tenant.full_name,
            "total_arrears": tenant.total_arrears()
        })


class LeaseViewSet(viewsets.ModelViewSet):
    serializer_class = LeaseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Lease.objects.filter(unit__property__owner=self.request.user)


from rest_framework.views import APIView
from django.db.models import Sum
from billing.models import Invoice
from django.utils import timezone


class DashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        today = timezone.now().date()

        properties_count = user.properties.count()
        tenants_count = sum(p.tenants.count() for p in user.properties.all())

        invoices_this_month = Invoice.objects.filter(
            lease__unit__property__owner=user,
            created_at__year=today.year,
            created_at__month=today.month
        )

        expected_rent = invoices_this_month.aggregate(
            total=Sum("amount")
        )["total"] or 0

        collected = sum(inv.total_paid() for inv in invoices_this_month)

        arrears = sum(
            tenant.total_arrears()
            for p in user.properties.all()
            for tenant in p.tenants.all()
        )

        total_units = sum(p.units.count() for p in user.properties.all())
        occupied_units = sum(
            p.units.filter(is_occupied=True).count()
            for p in user.properties.all()
        )

        occupancy_rate = (
            (occupied_units / total_units) * 100
            if total_units > 0 else 0
        )

        return Response({
            "properties": properties_count,
            "tenants": tenants_count,
            "expected_rent_this_month": expected_rent,
            "collected_this_month": collected,
            "total_arrears": arrears,
            "occupancy_rate_percent": round(occupancy_rate, 2),
        })
