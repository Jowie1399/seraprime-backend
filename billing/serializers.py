# billing/serializers.py
from decimal import Decimal
from rest_framework import serializers
from .models import Invoice, Receipt


class InvoiceSerializer(serializers.ModelSerializer):
    tenant_name = serializers.CharField(source="lease.tenant.full_name", read_only=True)
    tenant_id = serializers.IntegerField(source="lease.tenant.id", read_only=True)
    unit_name = serializers.CharField(source="lease.unit.name", read_only=True)
    unit_id = serializers.IntegerField(source="lease.unit.id", read_only=True)
    property_name = serializers.CharField(source="lease.unit.property.name", read_only=True)
    property_id = serializers.IntegerField(source="lease.unit.property.id", read_only=True)
    property_number = serializers.CharField(source="lease.unit.property.property_number", read_only=True)
    total_paid = serializers.SerializerMethodField()
    balance = serializers.SerializerMethodField()
    receipt_count = serializers.SerializerMethodField()

    class Meta:
        model = Invoice
        fields = [
            "id",
            "invoice_number",
            "lease",
            "amount",
            "due_date",
            "status",
            "created_at",
            "tenant_id",
            "tenant_name",
            "unit_id",
            "unit_name",
            "property_id",
            "property_name",
            "property_number",
            "total_paid",
            "balance",
            "receipt_count",
        ]
        read_only_fields = [
            "invoice_number",
            "created_at",
            "tenant_id",
            "tenant_name",
            "unit_id",
            "unit_name",
            "property_id",
            "property_name",
            "property_number",
            "total_paid",
            "balance",
            "receipt_count",
        ]

    def get_total_paid(self, obj):
        return str(Decimal(obj.total_paid()))

    def get_balance(self, obj):
        return str(Decimal(obj.balance()))

    def get_receipt_count(self, obj):
        return obj.receipts.count()


class ReceiptSerializer(serializers.ModelSerializer):
    invoice_number = serializers.CharField(source="invoice.invoice_number", read_only=True)
    invoice_id = serializers.IntegerField(source="invoice.id", read_only=True)
    tenant_name = serializers.CharField(source="invoice.lease.tenant.full_name", read_only=True)
    tenant_id = serializers.IntegerField(source="invoice.lease.tenant.id", read_only=True)
    unit_name = serializers.CharField(source="invoice.lease.unit.name", read_only=True)
    unit_id = serializers.IntegerField(source="invoice.lease.unit.id", read_only=True)
    property_name = serializers.CharField(source="invoice.lease.unit.property.name", read_only=True)
    property_id = serializers.IntegerField(source="invoice.lease.unit.property.id", read_only=True)
    property_number = serializers.CharField(source="invoice.lease.unit.property.property_number", read_only=True)
    due_date = serializers.DateField(source="invoice.due_date", read_only=True)
    invoice_status = serializers.CharField(source="invoice.status", read_only=True)

    class Meta:
        model = Receipt
        fields = [
            "id",
            "invoice",
            "invoice_id",
            "invoice_number",
            "amount_paid",
            "payment_date",
            "source",
            "created_at",
            "tenant_id",
            "tenant_name",
            "unit_id",
            "unit_name",
            "property_id",
            "property_name",
            "property_number",
            "due_date",
            "invoice_status",
        ]
        read_only_fields = [
            "payment_date",
            "created_at",
            "invoice_id",
            "invoice_number",
            "tenant_id",
            "tenant_name",
            "unit_id",
            "unit_name",
            "property_id",
            "property_name",
            "property_number",
            "due_date",
            "invoice_status",
        ]