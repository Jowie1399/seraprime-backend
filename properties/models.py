

# Create your models here.
from django.db import models
from django.contrib.auth import get_user_model

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

    # Optional unique payment code (future use if needed)
    payment_identifier = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        db_index=True
    )

    wallet_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)

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
    unit = models.OneToOneField(Unit, on_delete=models.CASCADE, related_name="lease")
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="leases")
    rent_amount = models.DecimalField(max_digits=12, decimal_places=2)
    start_date = models.DateField()
    is_active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        if self.is_active:
            self.unit.is_occupied = True
        else:
            self.unit.is_occupied = False

        self.unit.save()

    def deactivate(self):
        self.is_active = False
        self.save()

    def __str__(self):
        return f"{self.tenant.full_name} - {self.unit.name}"
