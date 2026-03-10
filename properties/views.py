from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Sum

from .models import Property, Unit, Tenant, Lease
from .serializers import PropertySerializer, UnitSerializer, TenantSerializer, LeaseSerializer
from billing.models import Invoice
from rest_framework.decorators import action
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError

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
        invoices = [
            {
                "invoice_id": inv.id,
                "amount": inv.amount,
                "due_date": inv.due_date,
                "status": inv.status,
                "total_paid": inv.total_paid(),
                "balance": inv.balance(),
            }
            for lease in tenant.leases.all()
            for inv in lease.invoices.all()
        ]
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
    
    @action(detail=True, methods=["post"])
    def move_out(self, request, pk=None):

        tenant = self.get_object()

        if not tenant.is_active:
            raise ValidationError("Tenant already moved out.")

        lease = tenant.leases.filter(is_active=True).first()

        if not lease:
            raise ValidationError("No active lease found.")

        move_date = request.data.get("move_out_date")

        if not move_date:
            move_date = timezone.now().date()

        lease.end_lease(move_date)

        tenant.is_active = False
        tenant.move_out_date = move_date
        tenant.save()

        return Response({
            "message": "Tenant moved out successfully",
            "tenant": tenant.full_name,
            "unit": lease.unit.name,
            "move_out_date": move_date
        })

# views.py
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError
from .models import Lease
from .serializers import LeaseSerializer

class LeaseViewSet(viewsets.ModelViewSet):
    serializer_class = LeaseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Lease.objects.filter(unit__property__owner=self.request.user)

    def perform_create(self, serializer):
        unit = serializer.validated_data["unit"]
        if Lease.objects.filter(unit=unit, is_active=True).exists():
            raise ValidationError("This unit already has an active lease.")
        lease = serializer.save()
        unit.is_occupied = True
        unit.save()

    def perform_update(self, serializer):
        old_lease = self.get_object()
        new_unit = serializer.validated_data.get("unit", old_lease.unit)

        if new_unit != old_lease.unit and Lease.objects.filter(unit=new_unit, is_active=True).exists():
            raise ValidationError("This unit already has an active lease.")

        lease = serializer.save()

        # Update old unit occupancy if moved
        if old_lease.unit != new_unit:
            if not Lease.objects.filter(unit=old_lease.unit, is_active=True).exists():
                old_lease.unit.is_occupied = False
                old_lease.unit.save()
            new_unit.is_occupied = True
            new_unit.save()

    def perform_destroy(self, instance):
        unit = instance.unit
        instance.delete()
        if not Lease.objects.filter(unit=unit, is_active=True).exists():
            unit.is_occupied = False
            unit.save()


from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum
from django.utils import timezone

from .models import Property, Unit, Tenant, Lease
from billing.models import Invoice, Receipt


class DashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        user = request.user

        # Properties owned by user
        properties = Property.objects.filter(owner=user)

        property_count = properties.count()

        # Units belonging to these properties
        units = Unit.objects.filter(property__in=properties)

        total_units = units.count()
        occupied_units = units.filter(is_occupied=True).count()

        # Tenants
        tenants = Tenant.objects.filter(property__in=properties, is_active=True)
        tenant_count = tenants.count()

        # Active leases
        leases = Lease.objects.filter(unit__in=units, is_active=True)

        # Expected rent this month
        expected_rent = leases.aggregate(
            total=Sum("rent_amount")
        )["total"] or 0

        # Collected this month
        now = timezone.now()

        collected = Receipt.objects.filter(
            invoice__lease__unit__in=units,
            payment_date__year=now.year,
            payment_date__month=now.month
        ).aggregate(total=Sum("amount_paid"))["total"] or 0

        # Total arrears
        unpaid_invoices = Invoice.objects.filter(
            lease__unit__in=units,
            status__in=["unpaid", "partial", "past_due"]
        )

        arrears = sum(inv.balance() for inv in unpaid_invoices)

        # Occupancy rate
        occupancy_rate = 0
        if total_units > 0:
            occupancy_rate = round((occupied_units / total_units) * 100, 2)

        data = {
            "properties": property_count,
            "tenants": tenant_count,
            "expected_rent_this_month": expected_rent,
            "collected_this_month": collected,
            "total_arrears": arrears,
            "occupancy_rate_percent": occupancy_rate,
        }

        return Response(data)            