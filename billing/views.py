# billing/views.py
from django.db.models import Q
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Invoice, Receipt
from .serializers import InvoiceSerializer, ReceiptSerializer
from .tasks import generate_monthly_invoices_for_owner, notify_past_due_invoices


class InvoiceViewSet(viewsets.ModelViewSet):
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = (
            Invoice.objects
            .filter(lease__unit__property__owner=self.request.user)
            .select_related(
                "lease",
                "lease__tenant",
                "lease__unit",
                "lease__unit__property",
            )
            .prefetch_related("receipts")
            .order_by("-created_at")
        )

        status_param = self.request.query_params.get("status")
        property_id = self.request.query_params.get("property")
        tenant_id = self.request.query_params.get("tenant")
        unit_id = self.request.query_params.get("unit")
        date_from = self.request.query_params.get("date_from")
        date_to = self.request.query_params.get("date_to")
        search = self.request.query_params.get("search")

        if status_param:
            queryset = queryset.filter(status=status_param)

        if property_id:
            queryset = queryset.filter(lease__unit__property_id=property_id)

        if tenant_id:
            queryset = queryset.filter(lease__tenant_id=tenant_id)

        if unit_id:
            queryset = queryset.filter(lease__unit_id=unit_id)

        if date_from:
            queryset = queryset.filter(due_date__gte=date_from)

        if date_to:
            queryset = queryset.filter(due_date__lte=date_to)

        if search:
            queryset = queryset.filter(
                Q(invoice_number__icontains=search) |
                Q(lease__tenant__full_name__icontains=search) |
                Q(lease__unit__name__icontains=search) |
                Q(lease__unit__property__name__icontains=search) |
                Q(lease__unit__property__property_number__icontains=search)
            )

        return queryset

    @action(detail=False, methods=["post"])
    def generate_monthly(self, request):
        count = generate_monthly_invoices_for_owner(request.user.id)
        return Response({
            "message": "Monthly invoices generated.",
            "invoices_created": count
        })


class ReceiptViewSet(viewsets.ModelViewSet):
    serializer_class = ReceiptSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = (
            Receipt.objects
            .filter(invoice__lease__unit__property__owner=self.request.user)
            .select_related(
                "invoice",
                "invoice__lease",
                "invoice__lease__tenant",
                "invoice__lease__unit",
                "invoice__lease__unit__property",
            )
            .order_by("-payment_date", "-created_at")
        )

        property_id = self.request.query_params.get("property")
        tenant_id = self.request.query_params.get("tenant")
        unit_id = self.request.query_params.get("unit")
        invoice_id = self.request.query_params.get("invoice")
        source = self.request.query_params.get("source")
        date_from = self.request.query_params.get("date_from")
        date_to = self.request.query_params.get("date_to")
        search = self.request.query_params.get("search")

        if property_id:
            queryset = queryset.filter(invoice__lease__unit__property_id=property_id)

        if tenant_id:
            queryset = queryset.filter(invoice__lease__tenant_id=tenant_id)

        if unit_id:
            queryset = queryset.filter(invoice__lease__unit_id=unit_id)

        if invoice_id:
            queryset = queryset.filter(invoice_id=invoice_id)

        if source:
            queryset = queryset.filter(source__iexact=source)

        if date_from:
            queryset = queryset.filter(payment_date__date__gte=date_from)

        if date_to:
            queryset = queryset.filter(payment_date__date__lte=date_to)

        if search:
            queryset = queryset.filter(
                Q(invoice__invoice_number__icontains=search) |
                Q(invoice__lease__tenant__full_name__icontains=search) |
                Q(invoice__lease__unit__name__icontains=search) |
                Q(invoice__lease__unit__property__name__icontains=search) |
                Q(invoice__lease__unit__property__property_number__icontains=search) |
                Q(source__icontains=search)
            )

        return queryset


from django.http import JsonResponse
from django.contrib.auth.decorators import login_required


@login_required
def trigger_monthly_invoices(request):
    count = generate_monthly_invoices_for_owner(request.user.id)
    return JsonResponse({"message": f"{count} invoices generated for this month."})


@login_required
def trigger_past_due_notifications(request):
    notify_past_due_invoices()
    return JsonResponse({"message": "Past-due invoices updated and notifications sent."})