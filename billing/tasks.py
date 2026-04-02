from celery import shared_task
from django.utils import timezone
from datetime import date
from calendar import monthrange
from dateutil.relativedelta import relativedelta

from properties.models import Lease
from .models import Invoice
from notifications.utils import notify_user_devices


@shared_task
def generate_monthly_invoices_for_owner(owner_id):
    today = timezone.now().date()

    # 📅 First day of current month
    current_month_start = date(today.year, today.month, 1)

    active_leases = Lease.objects.filter(
        is_active=True,
        unit__property__owner_id=owner_id
    )

    created_count = 0

    for lease in active_leases:

        # 🚫 Skip leases that haven’t started yet
        if lease.start_date > today:
            continue

        # 📅 Start from lease start month
        month_cursor = date(
            lease.start_date.year,
            lease.start_date.month,
            1
        )

        # 🔁 Loop month-by-month until current month
        while month_cursor <= current_month_start:

            # 🚫 Prevent duplicate invoices
            exists = Invoice.objects.filter(
                lease=lease,
                due_date__year=month_cursor.year,
                due_date__month=month_cursor.month,
            ).exists()

            if not exists:

                # 📆 Handle different due days safely
                last_day = monthrange(month_cursor.year, month_cursor.month)[1]

                # fallback to 5 if field not yet added
                due_day = getattr(lease, "due_day", 5)
                due_day = min(due_day, last_day)

                due_date = date(
                    month_cursor.year,
                    month_cursor.month,
                    due_day
                )

                Invoice.objects.create(
                    lease=lease,
                    amount=lease.rent_amount,
                    due_date=due_date,
                )

                created_count += 1

            # ➡️ Move to next month
            month_cursor += relativedelta(months=1)

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
            body=f"{invoice.lease.tenant.full_name}'s rent is past due."
        )