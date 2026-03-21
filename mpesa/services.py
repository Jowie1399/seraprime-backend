import re
from django.db import transaction
from properties.models import Property, Unit
from billing.models import Invoice
from .models import MpesaTransaction


def normalize_reference(reference: str):
    if not reference:
        return ""
    return re.sub(r"\s+", "", str(reference).upper())


def normalize_unit(unit: str):
    if not unit:
        return ""
    return re.sub(r"[^A-Z0-9]", "", str(unit).upper())


def process_transaction(transaction_obj: MpesaTransaction, notify_landlady=True):
    with transaction.atomic():
        transaction_locked = (
            MpesaTransaction.objects
            .select_for_update()
            .select_related("property", "unit", "tenant", "invoice")
            .get(id=transaction_obj.id)
        )

        if transaction_locked.is_processed:
            return transaction_locked

        ref = normalize_reference(transaction_locked.account_reference)
        match = re.match(r"(\d+)(.*)", ref)

        if not match:
            transaction_locked.is_processed = True
            transaction_locked.save(update_fields=["is_processed"])
            return transaction_locked

        property_number = match.group(1)
        unit_part = normalize_unit(match.group(2))

        property_obj = Property.objects.filter(
            property_number=property_number
        ).first()

        if not property_obj:
            transaction_locked.is_processed = True
            transaction_locked.save(update_fields=["is_processed"])
            return transaction_locked

        transaction_locked.property = property_obj

        if unit_part:
            unit_obj = Unit.objects.filter(
                property=property_obj,
                name__iexact=unit_part
            ).first()

            if not unit_obj:
                normalized_units = Unit.objects.filter(property=property_obj)
                for u in normalized_units:
                    if normalize_unit(u.name) == unit_part:
                        unit_obj = u
                        break

            if unit_obj:
                transaction_locked.unit = unit_obj

                lease = unit_obj.leases.filter(is_active=True).select_related("tenant").first()

                if lease:
                    transaction_locked.tenant = lease.tenant

                    invoice = (
                        Invoice.objects
                        .select_for_update()
                        .filter(
                            lease=lease,
                            status__in=["unpaid", "partial", "past_due"]
                        )
                        .order_by("due_date", "created_at")
                        .first()
                    )

                    if invoice and not transaction_locked.is_matched:
                        invoice.apply_payment(transaction_locked.amount)
                        transaction_locked.invoice = invoice
                        transaction_locked.is_matched = True

        transaction_locked.is_processed = True
        transaction_locked.save(
            update_fields=[
                "property",
                "unit",
                "tenant",
                "invoice",
                "is_matched",
                "is_processed",
            ]
        )

        return transaction_locked