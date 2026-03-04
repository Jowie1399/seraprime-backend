from rest_framework import serializers
from .models import MpesaTransaction


class MpesaTransactionSerializer(serializers.ModelSerializer):
    property_name = serializers.CharField(source="property.name", read_only=True)
    property_number = serializers.CharField(source="property.property_number", read_only=True)
    unit_name = serializers.CharField(source="unit.name", read_only=True)
    tenant_name = serializers.CharField(source="tenant.full_name", read_only=True)
    invoice_id = serializers.IntegerField(source="invoice.id", read_only=True)

    class Meta:
        model = MpesaTransaction
        fields = "__all__"