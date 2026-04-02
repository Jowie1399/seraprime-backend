from rest_framework import serializers
from .models import Property, Unit, Tenant, Lease


class PropertySerializer(serializers.ModelSerializer):
    class Meta:
        model = Property
        fields = "__all__"
        read_only_fields = ("owner",)


class UnitSerializer(serializers.ModelSerializer):
    property_name = serializers.CharField(source="property.name", read_only=True)

    class Meta:
        model = Unit
        fields = "__all__"


class TenantSerializer(serializers.ModelSerializer):
    property_name = serializers.CharField(source="property.name", read_only=True)
    total_arrears = serializers.SerializerMethodField()

    class Meta:
        model = Tenant
        fields = "__all__"

    def get_total_arrears(self, obj):
        return  float(obj.total_arrears() or 0)


class LeaseSerializer(serializers.ModelSerializer):
    tenant_name = serializers.CharField(source="tenant.full_name", read_only=True)
    unit_name = serializers.CharField(source="unit.name", read_only=True)

    class Meta:
        model = Lease
        fields = "__all__"