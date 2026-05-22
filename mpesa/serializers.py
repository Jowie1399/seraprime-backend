# mpesa/serializers.py
from rest_framework import serializers

from .models import MpesaTransaction
from properties.models import Property, Unit, Tenant
from billing.models import Invoice


class MpesaTransactionSerializer(serializers.ModelSerializer):
    property_name = serializers.CharField(source="property.name", read_only=True)
    property_number = serializers.CharField(source="property.property_number", read_only=True)
    unit_name = serializers.CharField(source="unit.name", read_only=True)
    tenant_name = serializers.CharField(source="tenant.full_name", read_only=True)
    invoice_number = serializers.CharField(source="invoice_number", read_only=True)

    class Meta:
        model = MpesaTransaction
        fields = [
            "id",
            "receipt_number",
            "phone_number",
            "amount",
            "account_reference",
            "transaction_date",
            "property",
            "property_name",
            "property_number",
            "unit",
            "unit_name",
            "tenant",
            "tenant_name",
            "invoice",
            "invoice_number",
            "is_processed",
            "is_matched",
            "raw_payload",
            "created_at",
        ]
        read_only_fields = [
            "is_processed",
            "is_matched",
            "raw_payload",
            "created_at",
            "property_name",
            "property_number",
            "unit_name",
            "tenant_name",
            "invoice_number",
        ]

    def validate_property(self, value):
        request = self.context.get("request")
        if value and value.owner != request.user:
            raise serializers.ValidationError("You can only use your own property.")
        return value

    def validate_unit(self, value):
        request = self.context.get("request")
        if value and value.property.owner != request.user:
            raise serializers.ValidationError("You can only use your own unit.")
        return value

    def validate_tenant(self, value):
        request = self.context.get("request")
        if value and value.property.owner != request.user:
            raise serializers.ValidationError("You can only use your own tenant.")
        return value

    def validate_invoice(self, value):
        request = self.context.get("request")
        if value and value.lease.unit.property.owner != request.user:
            raise serializers.ValidationError("You can only use your own invoice.")
        return value

    def validate(self, attrs):
        request = self.context.get("request")
        property_obj = attrs.get("property")
        unit_obj = attrs.get("unit")
        tenant_obj = attrs.get("tenant")
        invoice_obj = attrs.get("invoice")

        instance = getattr(self, "instance", None)

        if instance:
            property_obj = property_obj if "property" in attrs else instance.property
            unit_obj = unit_obj if "unit" in attrs else instance.unit
            tenant_obj = tenant_obj if "tenant" in attrs else instance.tenant
            invoice_obj = invoice_obj if "invoice" in attrs else instance.invoice

        if property_obj and property_obj.owner != request.user:
            raise serializers.ValidationError({"property": "Invalid property."})

        if unit_obj:
            if unit_obj.property.owner != request.user:
                raise serializers.ValidationError({"unit": "Invalid unit."})
            if property_obj and unit_obj.property_id != property_obj.id:
                raise serializers.ValidationError({
                    "unit": "Selected unit does not belong to the selected property."
                })

        if tenant_obj:
            if tenant_obj.property.owner != request.user:
                raise serializers.ValidationError({"tenant": "Invalid tenant."})
            if property_obj and tenant_obj.property_id != property_obj.id:
                raise serializers.ValidationError({
                    "tenant": "Selected tenant does not belong to the selected property."
                })

        if invoice_obj:
            invoice_property = invoice_obj.lease.unit.property
            invoice_unit = invoice_obj.lease.unit
            invoice_tenant = invoice_obj.lease.tenant

            if invoice_property.owner != request.user:
                raise serializers.ValidationError({"invoice": "Invalid invoice."})

            if property_obj and invoice_property.id != property_obj.id:
                raise serializers.ValidationError({
                    "invoice": "Selected invoice does not belong to the selected property."
                })

            if unit_obj and invoice_unit.id != unit_obj.id:
                raise serializers.ValidationError({
                    "invoice": "Selected invoice does not belong to the selected unit."
                })

            if tenant_obj and invoice_tenant.id != tenant_obj.id:
                raise serializers.ValidationError({
                    "invoice": "Selected invoice does not belong to the selected tenant."
                })

        return attrs