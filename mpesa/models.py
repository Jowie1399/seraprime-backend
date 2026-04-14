from django.db import models
from properties.models import Property, Unit, Tenant
from billing.models import Invoice
from django.conf import settings

class MpesaTransaction(models.Model):
    owner = models.ForeignKey(   # ✅ ADD THIS FIELD HERE
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="mpesa_transactions",
        null=True,      # ✅ ADD
        blank=True 
    )
    receipt_number = models.CharField(
        max_length=50,
        unique=True,
        db_index=True
    )
    phone_number = models.CharField(max_length=20)
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )
    account_reference = models.CharField(max_length=100)
    transaction_date = models.DateTimeField(
        null=True,
        blank=True
    )

    property = models.ForeignKey(
        Property,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="mpesa_transactions"
    )
    unit = models.ForeignKey(
        Unit,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="mpesa_transactions"
    )
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="mpesa_transactions"
    )
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="mpesa_transactions"
    )

    is_processed = models.BooleanField(default=False)
    is_matched = models.BooleanField(default=False)
    raw_payload = models.JSONField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.receipt_number} - KES {self.amount}"