from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from properties.models import Lease
from .models import Invoice
from notifications.utils import notify_user_devices


@shared_task
def generate_monthly_invoices_for_owner(owner_id):
    today = timezone.now().date()
    active_leases = Lease.objects.filter(
        is_active=True,
        unit__property__owner_id=owner_id
    )

    created_count = 0

    for lease in active_leases:
        existing = Invoice.objects.filter(
            lease=lease,
            created_at__year=today.year,
            created_at__month=today.month,
        ).exists()

        if not existing:
            Invoice.objects.create(
                lease=lease,
                amount=lease.rent_amount,
                due_date=today + timedelta(days=5),
            )
            created_count += 1

    return created_count


@shared_task
def notify_past_due_invoices():
    today = timezone.now().date()

    past_due_invoices = Invoice.objects.filter(
        due_date__lt=today,
        status__in=["unpaid", "partial"]
    )

    for invoice in past_due_invoices:
        invoice.status = "past_due"
        invoice.save()

        owner = invoice.lease.unit.property.owner

        notify_user_devices(
            owner,
            title="Invoice Past Due",
            body=f"{invoice.lease.tenant.name}'s rent is past due."
        )