from django.db import transaction
from django.db.models import Q

from properties.models import Property, Unit, Tenant
from billing.models import Invoice


def process_transaction(transaction_obj):
    """
    SINGLE SOURCE OF TRUTH for ALL M-Pesa processing.
    """

    if transaction_obj.is_processed:
        return transaction_obj

    account_ref = (transaction_obj.account_reference or "").strip()
    account_ref = account_ref.replace("-", " ")

    property_obj = None
    unit_obj = None
    tenant_obj = None
    invoice_obj = None

    # =========================
    # PARSE ACCOUNT REFERENCE
    # =========================
    parts = account_ref.split()

    property_number = None
    unit_part = None

    if len(parts) == 1:
        raw = parts[0]
        property_number = raw

        prop = Property.objects.filter(property_number=raw).first()

        if not prop and len(raw) > 1:
            prop_try = raw[:-1]
            unit_try = raw[-1]

            prop = Property.objects.filter(property_number=prop_try).first()
            if prop:
                property_number = prop_try
                unit_part = unit_try
            else:
                prop_try = raw[:-2]
                unit_try = raw[-2:]

                prop = Property.objects.filter(property_number=prop_try).first()
                if prop:
                    property_number = prop_try
                    unit_part = unit_try
    else:
        property_number = parts[0]
        unit_part = parts[1] if len(parts) > 1 else None

    # =========================
    # PROPERTY
    # =========================
    if property_number:
        property_obj = Property.objects.filter(
            property_number=property_number
        ).first()

    # =========================
    # UNIT
    # =========================
    if property_obj and unit_part:
        unit_obj = Unit.objects.filter(
            Q(name__iexact=unit_part) |
            Q(name__iexact=unit_part.replace(" ", "")),
            property=property_obj
        ).first()

    # =========================
    # TENANT (from unit)
    # =========================
    if unit_obj:
        tenant_obj = Tenant.objects.filter(
            unit=unit_obj,
            is_active=True
        ).first()

    
        # =========================
        # INVOICE PRIORITY (MANUAL FIRST)
        # =========================
    if transaction_obj.invoice:
        invoice_obj = transaction_obj.invoice

        # derive tenant/property/unit from invoice
        tenant_obj = invoice_obj.lease.tenant
        unit_obj = invoice_obj.lease.unit
        property_obj = unit_obj.property

    else:
        # fallback to auto matching
        if tenant_obj:
            invoice_obj = Invoice.objects.filter(
                lease__tenant=tenant_obj,
                is_deleted=False,
                lease__is_active=True,
                lease__tenant__is_active=True,
                status__in=["unpaid","partial","past_due"]
            ).order_by("due_date").first()
            
            
    # =========================
    # APPLY PAYMENT
    # =========================
    with transaction.atomic():

        if property_obj:
            transaction_obj.property = property_obj

        if unit_obj:
            transaction_obj.unit = unit_obj

        if tenant_obj:
            transaction_obj.tenant = tenant_obj

        if invoice_obj:
    # only apply if not already matched
            if not transaction_obj.is_matched:
                invoice_obj.apply_payment(transaction_obj.amount)

            transaction_obj.invoice = invoice_obj
            transaction_obj.tenant = tenant_obj
            transaction_obj.unit = unit_obj
            transaction_obj.property = property_obj
            transaction_obj.is_matched = True

        transaction_obj.is_processed = True
        transaction_obj.save()

    return transaction_obj