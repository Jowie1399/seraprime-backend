from rest_framework import serializers
from .models import Property, Unit, Tenant, Lease


class PropertySerializer(serializers.ModelSerializer):
    class Meta:
        model = Property
        fields = "__all__"
        read_only_fields = ("owner",)


class UnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Unit
        fields = "__all__"


class TenantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tenant
        fields = "__all__"


class LeaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lease
        fields = "__all__"
