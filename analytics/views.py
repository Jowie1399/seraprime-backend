from decimal import Decimal

from django.db.models import Sum, Count, Q
from django.db.models.functions import TruncMonth, TruncDay, TruncYear
from django.utils.dateparse import parse_date
from rest_framework.decorators import api_view
from rest_framework.response import Response

from billing.models import Invoice, Receipt
from properties.models import Unit, Property, Tenant, Lease
from django.utils import timezone


def _active_invoice_queryset(request):
    invoices = Invoice.objects.filter(
        is_deleted=False,
        lease__is_active=True,
        lease__tenant__is_active=True
    ).select_related(
        "lease",
        "lease__tenant",
        "lease__unit",
        "lease__unit__property"
    )

    return _apply_invoice_filters(
        invoices,
        request
    )


def _active_receipt_queryset(request):
    receipts = Receipt.objects.filter(
        invoice__is_deleted=False,
        invoice__lease__is_active=True,
        invoice__lease__tenant__is_active=True
    ).select_related(
        "invoice",
        "invoice__lease",
        "invoice__lease__tenant",
        "invoice__lease__unit",
        "invoice__lease__unit__property"
    )

    return _apply_receipt_filters(
        receipts,
        request)
    

def _filter_by_owner(queryset, request, property_lookup="property__owner"):
    user = request.user
    if user and user.is_authenticated:
        return queryset.filter(**{property_lookup: user})
    return queryset.none()


def _safe_date(value):
    if not value:
        return None
    return parse_date(value)

def _get_group_trunc(group_by):
    if group_by == "day":
        return TruncDay

    if group_by == "year":
        return TruncYear

    return TruncMonth

from datetime import datetime

def determine_grouping(
    start_date,
    end_date
):

    if not start_date or not end_date:
        return "month"

    days=(end_date-start_date).days

    if days<=60:
        return "day"

    if days<=730:
        return "month"

    return "year"


def _apply_invoice_filters(qs, request):
    start_date = _safe_date(request.GET.get("start_date"))
    end_date = _safe_date(request.GET.get("end_date"))
    property_number = request.GET.get("property_number")

    qs = _filter_by_owner(qs, request, "lease__unit__property__owner")

    if property_number:
        qs = qs.filter(lease__unit__property__property_number=property_number)
    if start_date:
        qs = qs.filter(due_date__gte=start_date)
    if end_date:
        qs = qs.filter(due_date__lte=end_date)

    return qs


def _apply_receipt_filters(qs, request):
    start_date = _safe_date(request.GET.get("start_date"))
    end_date = _safe_date(request.GET.get("end_date"))
    property_number = request.GET.get("property_number")

    qs = _filter_by_owner(qs, request, "invoice__lease__unit__property__owner")

    if property_number:
        qs = qs.filter(invoice__lease__unit__property__property_number=property_number)
    if start_date:
        qs = qs.filter(payment_date__gte=start_date)
    if end_date:
        qs = qs.filter(payment_date__lte=end_date)

    return qs


def _apply_unit_filters(qs, request):
    property_number = request.GET.get("property_number")

    qs = _filter_by_owner(qs, request, "property__owner")

    if property_number:
        qs = qs.filter(property__property_number=property_number)

    return qs


def _apply_property_filters(qs, request):
    user = request.user
    if user and user.is_authenticated:
        qs = qs.filter(owner=user)
    else:
        qs = qs.none()

    property_number = request.GET.get("property_number")
    if property_number:
        qs = qs.filter(property_number=property_number)

    return qs


def _apply_tenant_filters(
    qs,
    request
):

    property_number=(
        request.GET.get(
        "property_number"
    )
    )

    if request.user.is_authenticated:

        qs=qs.filter(
        leases__unit__property__owner=request.user
        ).distinct()

    else:
        qs=qs.none()

    if property_number:

        qs=qs.filter(
        leases__unit__property__property_number=
        property_number
        )

    return qs


@api_view(["GET"])
def property_list(request):
    properties = _apply_property_filters(Property.objects.all(), request).order_by("name", "property_number")
    data = [
        {
            "id": prop.id,
            "property_number": prop.property_number,
            "name": prop.name,
            "location": prop.location,
            "label": f"{prop.property_number} - {prop.name}",
        }
        for prop in properties
    ]
    return Response(data)


@api_view(["GET"])
def rent_trend(request):
    invoices = _active_invoice_queryset(
        request
    )

    start_date = _safe_date(
        request.GET.get(
            "start_date"
        )
    )

    end_date = _safe_date(
        request.GET.get(
            "end_date"
        )
    )

    group_by = request.GET.get(
        "group_by"
    )

    if not group_by:
        group_by = determine_grouping(
            start_date,
            end_date
        )

    trunc_function = (
        _get_group_trunc(
            group_by
        )
    )
    qs = (
        invoices
        .annotate(period=trunc_function("due_date"))
        .values("period")
        .annotate(total=Sum("amount"))
        .order_by("period")
    )

    data = []

    for item in qs:
        if not item["period"]:
            continue

        if group_by == "day":
            label = item["period"].strftime("%d %b")

        elif group_by == "year":
            label = item["period"].strftime("%Y")

        else:
            label = item["period"].strftime("%b %Y")

        data.append({
                "month": label,
                "label": label,
                "total": float(item["total"] or 0),
            })
    return Response(data)


@api_view(["GET"])
def receipts_trend(request):
    receipts = _active_receipt_queryset(request)

    start_date = _safe_date(
    request.GET.get(
        "start_date"
    )
    )

    end_date = _safe_date(
        request.GET.get(
            "end_date"
        )
    )

    group_by = request.GET.get(
        "group_by"
    )

    if not group_by:
        group_by = determine_grouping(
            start_date,
            end_date
        )

    trunc_function = (
        _get_group_trunc(
            group_by
        )
    )

    qs = (
        receipts
        .annotate(period=trunc_function("payment_date"))
        .values("period")
        .annotate(total=Sum("amount_paid"))
        .order_by("period")
    )

    data = []

    for item in qs:
        if not item["period"]:
            continue

        if group_by == "day":
            label = item["period"].strftime("%d %b")

        elif group_by == "year":
            label = item["period"].strftime("%Y")

        else:
            label = item["period"].strftime("%b %Y")

        data.append({
            "month": label,
            "label": label,
            "total": float(item["total"] or 0),
        })

    return Response(data)


@api_view(["GET"])
def occupancy_stats(request):
    units = _apply_unit_filters(Unit.objects.all(), request)

    total_units = units.count()
    occupied = Lease.objects.filter(
    is_active=True,
    tenant__is_active=True,
    unit__property__owner=request.user
)

    property_number = request.GET.get(
        "property_number"
    )

    if property_number:
        occupied = occupied.filter(
            unit__property__property_number=
            property_number
        )

    occupied = occupied.values(
        "unit"
    ).distinct().count()
    vacant = total_units - occupied

    occupancy_rate = 0
    if total_units > 0:
        occupancy_rate = round((occupied / total_units) * 100, 1)

    data = {
        "total_units": total_units,
        "occupied": occupied,
        "vacant": vacant,
        "occupancy_rate": occupancy_rate,
    }
    return Response(data)


@api_view(["GET"])
def revenue_summary(request):
    """
    Actual collected revenue from receipts.
    """
    receipts = _active_receipt_queryset(request)
    total = receipts.aggregate(total=Sum("amount_paid"))["total"] or 0

    return Response({
        "total_revenue": float(total)
    })


@api_view(["GET"])
def dashboard_summary(request):
    properties = _apply_property_filters(Property.objects.all(), request)
    units = _apply_unit_filters(Unit.objects.all(), request)
    tenants = _apply_tenant_filters(
    Tenant.objects.filter(
        is_active=True
    ),
    request)
    
    leases=Lease.objects.filter(
    is_active=True,
    tenant__is_active=True
    )

    if request.user.is_authenticated:

        leases=leases.filter(
        unit__property__owner=request.user
        )

    else:

        leases=leases.none()

    property_number = request.GET.get("property_number")
    if property_number:
        leases = leases.filter(unit__property__property_number=property_number)
        
    invoices = _active_invoice_queryset(request)
    receipts = _active_receipt_queryset(request)

    total_properties = properties.count()
    total_units = units.count()
    active_occupied_units = leases.values(
        "unit"
    ).distinct()

    occupied_units = active_occupied_units.count()

    vacant_units = total_units - occupied_units
    active_tenants = tenants.count()
    active_leases = leases.count()

    total_billed = invoices.aggregate(total=Sum("amount"))["total"] or Decimal("0")
    total_collected = receipts.aggregate(total=Sum("amount_paid"))["total"] or Decimal("0")

    invoice_status_counts = invoices.aggregate(
        paid=Count("id", filter=Q(status="paid")),
        partial=Count("id", filter=Q(status="partial")),
        unpaid=Count("id", filter=Q(status="unpaid")),
        past_due=Count("id", filter=Q(status="past_due")),
    )

    arrears_total = Decimal("0")
    arrears_invoices = invoices.filter(status__in=["unpaid", "partial", "past_due"]).select_related(
        "lease", "lease__tenant", "lease__unit", "lease__unit__property"
    )
    for invoice in arrears_invoices:

        try:

            balance=invoice.balance()

            if balance and balance>0:

                arrears_total+=Decimal(
                balance
                )

        except Exception as e:

            print(
            "Invoice analytics error:",
            e
            )

            continue

    occupancy_rate = 0
    if total_units > 0:
        occupancy_rate = round((occupied_units / total_units) * 100, 1)

    collection_rate = 0
    if total_billed > 0:
        collection_rate = round((float(total_collected) / float(total_billed)) * 100, 1)

    data = {
        "total_properties": total_properties,
        "total_units": total_units,
        "occupied_units": occupied_units,
        "vacant_units": vacant_units,
        "occupancy_rate": occupancy_rate,
        "active_tenants": active_tenants,
        "active_leases": active_leases,
        "total_billed": float(total_billed),
        "total_collected": float(total_collected),
        "arrears_total": float(arrears_total),
        "collection_rate": collection_rate,
        "paid_invoices": invoice_status_counts["paid"] or 0,
        "partial_invoices": invoice_status_counts["partial"] or 0,
        "unpaid_invoices": invoice_status_counts["unpaid"] or 0,
        "past_due_invoices": invoice_status_counts["past_due"] or 0,
    }
    return Response(data)


@api_view(["GET"])
def invoice_receipt_comparison(request):
    invoices = _active_invoice_queryset(request)
    receipts = _active_receipt_queryset(request)

    total_invoiced = invoices.aggregate(total=Sum("amount"))["total"] or 0
    total_received = receipts.aggregate(total=Sum("amount_paid"))["total"] or 0

    outstanding = Decimal(str(total_invoiced)) - Decimal(str(total_received))
    if outstanding < 0:
        outstanding = Decimal("0")

    return Response({
        "total_invoiced": float(total_invoiced),
        "total_received": float(total_received),
        "outstanding": float(outstanding),
    })