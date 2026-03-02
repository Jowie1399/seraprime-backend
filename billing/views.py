from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Invoice, Receipt
from .serializers import InvoiceSerializer, ReceiptSerializer
from .tasks import generate_monthly_invoices_for_owner


class InvoiceViewSet(viewsets.ModelViewSet):
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Invoice.objects.filter(
            lease__unit__property__owner=self.request.user
        )

    @action(detail=False, methods=["post"])
    def generate_monthly(self, request):
        count = generate_monthly_invoices_for_owner(request.user)
        return Response({
            "message": "Monthly invoices generated.",
            "invoices_created": count
        })


class ReceiptViewSet(viewsets.ModelViewSet):
    serializer_class = ReceiptSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Receipt.objects.filter(
            invoice__lease__unit__property__owner=self.request.user
        )

from django.http import JsonResponse
from .tasks import generate_monthly_invoices_for_owner, notify_past_due_invoices
from django.contrib.auth.decorators import login_required

@login_required
def trigger_monthly_invoices(request):
    owner_id = request.user.id
    count = generate_monthly_invoices_for_owner(owner_id)
    return JsonResponse({"message": f"{count} invoices generated for this month."})

@login_required
def trigger_past_due_notifications(request):
    notify_past_due_invoices()
    return JsonResponse({"message": "Past-due invoices updated and notifications sent."})