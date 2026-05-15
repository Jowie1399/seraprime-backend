from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from django.db.models import Sum
from rest_framework.views import APIView

from .models import Property, Unit, Tenant, Lease
from .serializers import PropertySerializer, UnitSerializer, TenantSerializer, LeaseSerializer
from billing.models import Invoice, Receipt


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

        active_lease = tenant.leases.filter(
            is_active=True
        ).first()

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

            "current_arrears": tenant.total_arrears(),

            "rent_amount":
                active_lease.rent_amount
                if active_lease else None,

            "deposit_amount":
                active_lease.deposit_amount
                if active_lease else None,

            "opening_arrears":
                active_lease.opening_arrears
                if active_lease else None,

            "billing_start_date":
                active_lease.billing_start_date
                if active_lease else None,

            "move_in_date":
                active_lease.start_date
                if active_lease else None,

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

        move_date = request.data.get("move_out_date") or timezone.now().date()
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

        old_unit = old_lease.unit

        new_unit = serializer.validated_data.get(
            "unit",
            old_unit
        )

        if (
            new_unit != old_unit and
            Lease.objects.filter(
                unit=new_unit,
                is_active=True
            ).exclude(
                pk=old_lease.pk
            ).exists()
        ):

            raise ValidationError(
                "This unit already has an active lease."
            )

        lease = serializer.save()

        # old unit occupancy cleanup
        if old_unit != new_unit:

            old_unit.is_occupied = Lease.objects.filter(
                unit=old_unit,
                is_active=True
            ).exclude(
                pk=lease.pk
            ).exists()

            old_unit.save()

            new_unit.is_occupied=True
            new_unit.save()

    def perform_destroy(self, instance):
        unit = instance.unit
        instance.delete()
        if not Lease.objects.filter(unit=unit, is_active=True).exists():
            unit.is_occupied = False
            unit.save()


from decimal import Decimal
from django.db.models import Sum
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Property, Unit, Tenant, Lease
from billing.models import Invoice, Receipt


class DashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        today = timezone.now().date()

        current_month = today.month
        current_year = today.year

        properties = Property.objects.filter(owner=user)

        units = Unit.objects.filter(property__in=properties)

        active_leases = Lease.objects.filter(
            unit__in=units,
            is_active=True,
            tenant__is_active=True,
        )

        active_tenants = Tenant.objects.filter(
            property__in=properties,
            is_active=True,
        )

        invoices = Invoice.objects.filter(
            lease__in=active_leases
        )

        receipts = Receipt.objects.filter(
            invoice__lease__in=active_leases
        )

        # CURRENT MONTH INVOICES
        current_month_invoices = invoices.filter(
            due_date__year=current_year,
            due_date__month=current_month,
        )

        # CURRENT MONTH RECEIPTS
        current_month_receipts = receipts.filter(
            payment_date__year=current_year,
            payment_date__month=current_month,
        )

        # EXPECTED RENT THIS MONTH
        expected_rent = current_month_invoices.aggregate(
            total=Sum("amount")
        )["total"] or Decimal("0")

        # COLLECTED THIS MONTH
        collected_this_month = current_month_receipts.aggregate(
            total=Sum("amount_paid")
        )["total"] or Decimal("0")

        # CURRENT MONTH ARREARS
        current_month_arrears = Decimal("0")

        current_unpaid = current_month_invoices.filter(
            status__in=["unpaid", "partial", "past_due"]
        )

        for invoice in current_unpaid:
            balance = invoice.balance()
            if balance > 0:
                current_month_arrears += Decimal(balance)

        # HISTORICAL ARREARS
        historical_arrears = Decimal("0")

        historical_invoices = invoices.filter(
            due_date__lt=today
        ).exclude(
            due_date__year=current_year,
            due_date__month=current_month,
        ).filter(
            status__in=["unpaid", "partial", "past_due"]
        )

        for invoice in historical_invoices:
            balance = invoice.balance()
            if balance > 0:
                historical_arrears += Decimal(balance)

        property_count = properties.count()

        total_units = units.count()

        occupied_units = units.filter(
            is_occupied=True
        ).count()

        tenant_count = active_tenants.count()

        occupancy_rate = (
            round((occupied_units / total_units) * 100, 2)
            if total_units > 0 else 0
        )

        return Response({
            "properties": property_count,
            "tenants": tenant_count,

            "expected_rent_this_month": float(expected_rent),

            "collected_this_month": float(collected_this_month),

            "current_month_arrears": float(current_month_arrears),

            "historical_arrears": float(historical_arrears),

            "occupancy_rate_percent": occupancy_rate,
        })