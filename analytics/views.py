# analytics/views.py
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db.models import Sum, Count
from django.db.models.functions import TruncMonth
from billing.models import Invoice
from properties.models import Unit, Property
from django.utils.dateparse import parse_date


@api_view(["GET"])
def rent_trend(request):
    """
    Returns rent collected grouped by month.
    Optional filters:
        start_date=YYYY-MM-DD
        end_date=YYYY-MM-DD
        property_number=<property_number>
    """
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")
    property_number = request.GET.get("property_number")

    invoices = Invoice.objects.all()

    if property_number:
        invoices = invoices.filter(lease__unit__property__property_number=property_number)
    if start_date:
        invoices = invoices.filter(created_at__date__gte=parse_date(start_date))
    if end_date:
        invoices = invoices.filter(created_at__date__lte=parse_date(end_date))

    qs = (
        invoices
        .annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(total=Sum("amount"))
        .order_by("month")
    )

    data = [
        {"month": i["month"].strftime("%b"), "total": i["total"] or 0}
        for i in qs
    ]

    return Response(data)


@api_view(["GET"])
def occupancy_stats(request):
    """
    Returns occupied vs vacant units.
    Optional filter: property_number
    """
    property_number = request.GET.get("property_number")

    units = Unit.objects.all()
    if property_number:
        units = units.filter(property__property_number=property_number)

    total_units = units.count()
    occupied = units.filter(is_occupied=True).count()
    vacant = units.filter(is_occupied=False).count()

    data = {
        "total_units": total_units,
        "occupied": occupied,
        "vacant": vacant
    }
    return Response(data)


@api_view(["GET"])
def revenue_summary(request):
    """
    Returns total revenue collected.
    Optional filters:
        start_date, end_date, property_number
    """
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")
    property_number = request.GET.get("property_number")

    invoices = Invoice.objects.all()
    if property_number:
        invoices = invoices.filter(lease__unit__property__property_number=property_number)
    if start_date:
        invoices = invoices.filter(created_at__date__gte=parse_date(start_date))
    if end_date:
        invoices = invoices.filter(created_at__date__lte=parse_date(end_date))

    total = invoices.aggregate(total=Sum("amount"))["total"] or 0
    return Response({"total_revenue": total})