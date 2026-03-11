from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone

User = get_user_model()


class Property(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="properties")
    property_number = models.CharField(max_length=20, unique=True, db_index=True)
    name = models.CharField(max_length=255)
    location = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.property_number} - {self.name}"


class Unit(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="units")
    name = models.CharField(max_length=100)
    is_occupied = models.BooleanField(default=False)

    class Meta:
        unique_together = ("property", "name")

    def __str__(self):
        return f"{self.property.property_number} - {self.name}"


class Tenant(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="tenants")
    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20, db_index=True)
    national_id = models.CharField(max_length=20, blank=True, null=True, db_index=True)
    wallet_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    move_out_date = models.DateField(blank=True, null=True)

    def total_arrears(self):
        from billing.models import Invoice

        invoices = Invoice.objects.filter(
            lease__tenant=self,
            status__in=["unpaid", "partial", "past_due"]
        )
        return sum(inv.balance() for inv in invoices)

    def __str__(self):
        return self.full_name


class Lease(models.Model):
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name="leases")
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="leases")
    rent_amount = models.DecimalField(max_digits=12, decimal_places=2)
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["unit"],
                condition=models.Q(is_active=True),
                name="unique_active_lease_per_unit"
            )
        ]

    def save(self, *args, **kwargs):
        if self.is_active:
            existing = Lease.objects.filter(unit=self.unit, is_active=True)
            if self.pk:
                existing = existing.exclude(pk=self.pk)
            if existing.exists():
                raise ValidationError("This unit already has an active lease.")
        super().save(*args, **kwargs)
        self.unit.is_occupied = self.is_active
        self.unit.save()

    def end_lease(self, date=None):
        if date is None:
            date = timezone.now().date()
        self.is_active = False
        self.end_date = date
        self.save()

    def __str__(self):
        return f"{self.tenant.full_name} - {self.unit.name} ({'Active' if self.is_active else 'Inactive'})"