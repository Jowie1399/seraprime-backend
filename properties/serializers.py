from rest_framework import serializers
from .models import Property, Unit, Tenant, Lease
from datetime import date
from calendar import monthrange



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

    unit_name = serializers.SerializerMethodField()
    unit_id = serializers.SerializerMethodField()
    rent_amount = serializers.SerializerMethodField()   
    start_date = serializers.SerializerMethodField()  
    next_due_date = serializers.SerializerMethodField()
  

    class Meta:
        model = Tenant
        fields = "__all__"

    def get_total_arrears(self, obj):
        return float(obj.total_arrears() or 0)

    def get_unit_name(self, obj):
        lease = obj.leases.filter(is_active=True).first()
        return lease.unit.name if lease else None

    def get_unit_id(self, obj):
        lease = obj.leases.filter(is_active=True).first()
        return lease.unit.id if lease else None
    
    def get_rent_amount(self, obj):  #  ADDED THIS
        lease = obj.leases.filter(is_active=True).first()
        return str(lease.rent_amount) if lease else None
    
    def get_start_date(self, obj):
        lease = obj.leases.filter(is_active=True).first()
        return lease.start_date if lease else None
    

    def get_next_due_date(self, obj):
        lease = obj.leases.filter(is_active=True).first()

        if not lease:
            return None

        today = date.today()

        # current month due date
        last_day = monthrange(today.year, today.month)[1]
        due_day = min(lease.due_day, last_day)

        current_due = date(today.year, today.month, due_day)

        # if already passed → next month
        if current_due < today:
            if today.month == 12:
                year = today.year + 1
                month = 1
            else:
                year = today.year
                month = today.month + 1

            last_day = monthrange(year, month)[1]
            due_day = min(lease.due_day, last_day)

            return date(year, month, due_day)

        return current_due

class LeaseSerializer(serializers.ModelSerializer):
    tenant_name = serializers.CharField(source="tenant.full_name", read_only=True)
    unit_name = serializers.CharField(source="unit.name", read_only=True)

    class Meta:
        model = Lease
        fields = "__all__"