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
