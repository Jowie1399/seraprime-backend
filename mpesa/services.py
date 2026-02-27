import re
from properties.models import Property, Unit
from billing.models import Invoice
from .models import MpesaTransaction
from notifications.utils import notify_user_devices


def normalize_reference(reference: str):
    return re.sub(r"\s+", "", reference.upper())


def process_transaction(transaction: MpesaTransaction, notify_landlady=True):
    """
    Matches payment to property/unit/tenant and applies to invoice.
    Sends notification to landlady if enabled.
    """

    # Prevent double processing
    if transaction.is_processed:
        return

    ref = normalize_reference(transaction.account_reference)

    # Extract property number (numbers at start)
    match = re.match(r"(\d+)(.*)", ref)

    if not match:
        transaction.is_processed = True
        transaction.save()
        return

    property_number = match.group(1)
    unit_part = match.group(2)

    # Match Property
    try:
        property_obj = Property.objects.get(property_number=property_number)
        transaction.property = property_obj
    except Property.DoesNotExist:
        transaction.is_processed = True
        transaction.save()
        return

    # Match Unit
    if unit_part:
        try:
            unit_obj = Unit.objects.get(property=property_obj, name=unit_part)
            transaction.unit = unit_obj

            lease = unit_obj.lease

            if lease and lease.is_active:
                tenant = lease.tenant
                transaction.tenant = tenant

                invoice = Invoice.objects.filter(
                    lease=lease,
                    status__in=["unpaid", "partial", "past_due"]
                ).order_by("due_date").first()

                if invoice:
                    invoice.apply_payment(transaction.amount)
                    transaction.invoice = invoice
                    transaction.is_matched = True

                    # 🔔 Notify Landlady (if notifications app installed)
                    if notify_landlady:
                        try:
                            from notifications.utils import notify_user_devices

                            owner = property_obj.owner

                            notify_user_devices(
                                owner,
                                title="Payment Received",
                                body=f"{tenant.name} paid KES {transaction.amount}"
                            )
                        except Exception:
                            # Avoid breaking payment processing if notification fails
                            pass

        except Unit.DoesNotExist:
            pass

    transaction.is_processed = True
    transaction.save()