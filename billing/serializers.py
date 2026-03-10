from rest_framework import serializers
from .models import Invoice, Receipt


class InvoiceSerializer(serializers.ModelSerializer):

    class Meta:
        model = Invoice
        fields = "__all__"
        read_only_fields = ["invoice_number"]


class ReceiptSerializer(serializers.ModelSerializer):

    invoice_number = serializers.CharField(
        source="invoice.invoice_number",
        read_only=True
    )

    class Meta:
        model = Receipt
        fields = "__all__"