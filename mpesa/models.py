from django.db import models
from properties.models import Property, Unit, Tenant
from billing.models import Invoice

class MpesaTransaction(models.Model):
    receipt_number = models.CharField(max_length=50, unique=True)
    phone_number = models.CharField(max_length=20)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    account_reference = models.CharField(max_length=100)
    transaction_date = models.DateTimeField(null=True, blank=True)

    property = models.ForeignKey(
        Property,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    unit = models.ForeignKey(
        Unit,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    is_processed = models.BooleanField(default=False)
    is_matched = models.BooleanField(default=False)

    raw_payload = models.JSONField()

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.receipt_number} - {self.amount}"