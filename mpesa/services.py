import re

from django.db import transaction

from properties.models import Property, Unit
from billing.models import Invoice
from .models import MpesaTransaction


def normalize_reference(reference: str):
    if not reference:
        return ""
    return re.sub(r"\s+", "", reference.upper())


def normalize_unit(unit: str):
    """
    Removes symbols like - or _ from unit names.
    Example:
    101-A1 -> A1
    101_A1 -> A1
    """
    if not unit:
        return ""
    return re.sub(r"[^A-Z0-9]", "", unit.upper())


def process_transaction(transaction: MpesaTransaction, notify_landlady=True):

    # Lock transaction row so multiple workers cannot process it at the same time
    with transaction.atomic():

        transaction = (
            MpesaTransaction.objects
            .select_for_update()
            .get(id=transaction.id)
        )

        if transaction.is_processed:
            return

        ref = normalize_reference(transaction.account_reference)

        match = re.match(r"(\d+)(.*)", ref)

        if not match:
            transaction.is_processed = True
            transaction.save(update_fields=["is_processed"])
            return

        property_number = match.group(1)
        unit_part = normalize_unit(match.group(2))

        # SAFER property lookup
        property_obj = Property.objects.filter(
            property_number=property_number
        ).first()

        if not property_obj:
            transaction.is_processed = True
            transaction.save(update_fields=["is_processed"])
            return

        transaction.property = property_obj

        if unit_part:

            unit_obj = Unit.objects.filter(
                property=property_obj,
                name=unit_part
            ).first()

            if unit_obj:

                transaction.unit = unit_obj

                lease = getattr(unit_obj, "lease", None)

                if lease and lease.is_active:

                    tenant = lease.tenant
                    transaction.tenant = tenant

                    # LOCK invoice row to prevent race conditions
                    invoice = (
                        Invoice.objects
                        .select_for_update()
                        .filter(
                            lease=lease,
                            status__in=["unpaid", "partial", "past_due"]
                        )
                        .order_by("due_date")
                        .first()
                    )

                    if invoice and not transaction.is_matched:

                        invoice.apply_payment(transaction.amount)

                        transaction.invoice = invoice
                        transaction.is_matched = True

        transaction.is_processed = True

        transaction.save(
            update_fields=[
                "property",
                "unit",
                "tenant",
                "invoice",
                "is_matched",
                "is_processed"
            ]
        )