from django.db import models
from django.utils import timezone
from properties.models import Lease
from decimal import Decimal
import random
import string


def generate_invoice_number():
    date_part = timezone.now().strftime("%Y%m%d")
    random_part = ''.join(random.choices(string.digits, k=4))
    return f"INV-{date_part}-{random_part}"


class Invoice(models.Model):

    STATUS_CHOICES = [
        ("unpaid", "Unpaid"),
        ("partial", "Partial"),
        ("paid", "Paid"),
        ("past_due", "Past Due"),
    ]

    invoice_number = models.CharField(
        max_length=30,
        unique=True,
        editable=False,
        db_index=True,
        blank=True
    )

    lease = models.ForeignKey(
        Lease,
        on_delete=models.CASCADE,
        related_name="invoices"
    )

    amount = models.DecimalField(max_digits=12, decimal_places=2)

    due_date = models.DateField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="unpaid"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    is_deleted = models.BooleanField(default=False)

    deleted_at = models.DateTimeField(
        null=True,
        blank=True
    )

    def soft_delete(self):
        self.is_deleted=True
        self.deleted_at=timezone.now()
        self.save()
    
    

    # ---------- CORE CALCULATIONS ----------

    
    def total_paid(self):
        if self.is_deleted:
            return Decimal("0.00")

        return sum(
            (receipt.amount_paid for receipt in self.receipts.all()),
            Decimal("0.00")
        )
    def balance(self):
        return self.amount - Decimal(self.total_paid())

    # ---------- PAYMENT APPLICATION ----------

    def apply_payment(self, amount):

        tenant = self.lease.tenant
        remaining = self.balance()

        if remaining <= 0:
            tenant.wallet_balance += Decimal(amount)
            tenant.save()
            return

        if amount >= remaining:

            Receipt.objects.create(
                invoice=self,
                amount_paid=remaining
            )

            overpayment = Decimal(amount) - remaining

            if overpayment > 0:
                tenant.wallet_balance += overpayment
                tenant.save()

        else:

            Receipt.objects.create(
                invoice=self,
                amount_paid=Decimal(amount)
            )

        self.update_status()

    # ---------- WALLET AUTO APPLY ----------

    def apply_wallet(self):

        tenant = self.lease.tenant

        if tenant.wallet_balance <= 0 or self.status == "paid":
            return

        remaining = self.balance()

        if tenant.wallet_balance >= remaining:

            Receipt.objects.create(
                invoice=self,
                amount_paid=remaining
            )

            tenant.wallet_balance -= remaining

        else:

            Receipt.objects.create(
                invoice=self,
                amount_paid=tenant.wallet_balance
            )

            tenant.wallet_balance = Decimal("0")

        tenant.save()

        self.update_status()

    # ---------- STATUS ----------

    def update_status(self):

        paid = Decimal(self.total_paid())

        if paid >= self.amount:
            self.status = "paid"

        elif paid > 0:
            self.status = "partial"

        else:

            if self.due_date < timezone.now().date():
                self.status = "past_due"
            else:
                self.status = "unpaid"

        self.save(update_fields=["status"])

    # ---------- SAVE ----------

    def save(self, *args, **kwargs):

        if not self.invoice_number:
            self.invoice_number = generate_invoice_number()

        super().save(*args, **kwargs)

        self.apply_wallet()

    def __str__(self):
        return f"{self.invoice_number} - {self.lease.tenant.full_name}"


class Receipt(models.Model):

    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name="receipts"
    )

    amount_paid = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    payment_date = models.DateTimeField(auto_now_add=True)

    source = models.CharField(
        max_length=50,
        default="mpesa"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):

        super().save(*args, **kwargs)

        invoice = self.invoice
        tenant = invoice.lease.tenant

        overpayment = invoice.total_paid() - invoice.amount

        if overpayment > 0:
            tenant.wallet_balance += overpayment
            tenant.save()

        invoice.update_status()

    def __str__(self):
        return f"Receipt {self.id} - {self.invoice.invoice_number}"