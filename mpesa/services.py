import re

from properties.models import Property, Unit
from billing.models import Invoice
from .models import MpesaTransaction


def normalize_reference(reference: str):
    return re.sub(r"\s+", "", reference.upper())


def process_transaction(transaction: MpesaTransaction, notify_landlady=True):

    if transaction.is_processed:
        return

    ref = normalize_reference(transaction.account_reference)

    match = re.match(r"(\d+)(.*)", ref)

    if not match:
        transaction.is_processed = True
        transaction.save()
        return

    property_number = match.group(1)
    unit_part = match.group(2)

    try:

        property_obj = Property.objects.get(property_number=property_number)

        transaction.property = property_obj

    except Property.DoesNotExist:

        transaction.is_processed = True
        transaction.save()
        return

    if unit_part:

        try:

            unit_obj = Unit.objects.get(property=property_obj, name=unit_part)

            transaction.unit = unit_obj

            lease = getattr(unit_obj, "lease", None)

            if lease and lease.is_active:

                tenant = lease.tenant
                transaction.tenant = tenant

                invoice = Invoice.objects.filter(
                    lease=lease,
                    status__in=["unpaid", "partial", "past_due"]
                ).order_by("due_date").first()

                if invoice:

                    if not transaction.is_matched:

                        invoice.apply_payment(transaction.amount)

                        transaction.invoice = invoice
                        transaction.is_matched = True

        except Unit.DoesNotExist:
            pass

    transaction.is_processed = True
    transaction.save()