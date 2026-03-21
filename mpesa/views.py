# mpesa/views.py
from decimal import Decimal
from datetime import datetime

from django.db import transaction, IntegrityError
from django.db.models import Q

from rest_framework.decorators import (
    api_view,
    permission_classes,
    authentication_classes,
    action,
)
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status, viewsets

from .models import MpesaTransaction
from .services import process_transaction
from .serializers import MpesaTransactionSerializer
from billing.models import Invoice


def parse_mpesa_datetime(value):
    """
    Safaricom C2B TransTime often comes as YYYYMMDDHHMMSS
    Example: 20260318153045
    """
    if not value:
        return None

    try:
        return datetime.strptime(str(value), "%Y%m%d%H%M%S")
    except Exception:
        return None


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def mpesa_confirmation(request):
    print("\n🔥 C2B CONFIRMATION RECEIVED 🔥")

    receipt = request.data.get("TransID")
    amount = request.data.get("TransAmount")
    phone = request.data.get("MSISDN")
    account_ref = request.data.get("BillRefNumber")
    transaction_date = request.data.get("TransTime")

    if not receipt:
        return Response(
            {"ResultCode": 1, "ResultDesc": "Invalid receipt"},
            status=status.HTTP_200_OK,
        )

    try:
        amount_value = Decimal(str(amount)) if amount else Decimal("0")

        with transaction.atomic():
            transaction_obj = MpesaTransaction.objects.create(
                receipt_number=str(receipt),
                phone_number=str(phone or ""),
                amount=amount_value,
                account_reference=str(account_ref or ""),
                transaction_date=parse_mpesa_datetime(transaction_date),
                raw_payload=request.data,
            )

    except IntegrityError:
        return Response(
            {"ResultCode": 0, "ResultDesc": "Duplicate ignored"},
            status=status.HTTP_200_OK,
        )

    except Exception as e:
        print("❌ DB ERROR:", str(e))
        return Response(
            {"ResultCode": 0, "ResultDesc": "Accepted"},
            status=status.HTTP_200_OK,
        )

    try:
        process_transaction(transaction_obj)
    except Exception as e:
        print("❌ PROCESSING ERROR:", str(e))

    return Response(
        {"ResultCode": 0, "ResultDesc": "Confirmation received"},
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def mpesa_validation(request):
    print("\n🟡 VALIDATION REQUEST RECEIVED")
    return Response(
        {"ResultCode": 0, "ResultDesc": "Accepted"},
        status=status.HTTP_200_OK,
    )


class MpesaTransactionViewSet(viewsets.ModelViewSet):
    serializer_class = MpesaTransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = (
            MpesaTransaction.objects
            .filter(
                Q(property__owner=user) |
                Q(invoice__lease__unit__property__owner=user) |
                Q(unit__property__owner=user) |
                Q(tenant__property__owner=user)
            )
            .select_related(
                "property",
                "unit",
                "tenant",
                "invoice",
                "invoice__lease",
                "invoice__lease__tenant",
                "invoice__lease__unit",
                "invoice__lease__unit__property",
            )
            .distinct()
            .order_by("-created_at")
        )

        is_matched = self.request.query_params.get("is_matched")
        if is_matched in ["true", "false"]:
            qs = qs.filter(is_matched=(is_matched == "true"))

        property_id = self.request.query_params.get("property")
        if property_id:
            qs = qs.filter(property_id=property_id)

        unit_id = self.request.query_params.get("unit")
        if unit_id:
            qs = qs.filter(unit_id=unit_id)

        tenant_id = self.request.query_params.get("tenant")
        if tenant_id:
            qs = qs.filter(tenant_id=tenant_id)

        invoice_id = self.request.query_params.get("invoice")
        if invoice_id:
            qs = qs.filter(invoice_id=invoice_id)

        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(
                Q(receipt_number__icontains=search) |
                Q(phone_number__icontains=search) |
                Q(account_reference__icontains=search) |
                Q(property__name__icontains=search) |
                Q(property__property_number__icontains=search) |
                Q(unit__name__icontains=search) |
                Q(tenant__full_name__icontains=search) |
                Q(invoice__invoice_number__icontains=search)
            )

        return qs

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    def perform_create(self, serializer):
        transaction_obj = serializer.save()

        try:
            process_transaction(transaction_obj)
        except Exception as e:
            print("❌ Import processing error:", str(e))

    def perform_update(self, serializer):
        instance = serializer.save()

        if not instance.is_processed:
            try:
                process_transaction(instance)
            except Exception as e:
                print("❌ Re-processing error:", str(e))

    @action(detail=True, methods=["post"])
    def manually_allocate(self, request, pk=None):
        with transaction.atomic():
            transaction_obj = (
                self.get_queryset()
                .select_for_update()
                .select_related(
                    "property",
                    "unit",
                    "tenant",
                    "invoice",
                )
                .get(pk=pk)
            )

            if transaction_obj.is_matched:
                return Response(
                    {"error": "Transaction already matched."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            invoice_id = request.data.get("invoice_id")
            if not invoice_id:
                return Response(
                    {"error": "invoice_id is required."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                invoice = (
                    Invoice.objects
                    .select_for_update()
                    .select_related("lease__tenant", "lease__unit__property")
                    .get(
                        id=invoice_id,
                        lease__unit__property__owner=request.user,
                    )
                )
            except Invoice.DoesNotExist:
                return Response(
                    {"error": "Invalid invoice."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if invoice.status == "paid":
                return Response(
                    {"error": "This invoice is already fully paid."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            transaction_obj.invoice = invoice
            transaction_obj.tenant = invoice.lease.tenant
            transaction_obj.unit = invoice.lease.unit
            transaction_obj.property = invoice.lease.unit.property

            transaction_obj.full_clean(exclude=["raw_payload"])

            invoice.apply_payment(transaction_obj.amount)

            transaction_obj.is_matched = True
            transaction_obj.is_processed = True
            transaction_obj.save(
                update_fields=[
                    "invoice",
                    "tenant",
                    "unit",
                    "property",
                    "is_matched",
                    "is_processed",
                ]
            )

        return Response(
            {
                "message": "Payment allocated successfully",
                "transaction_id": transaction_obj.id,
                "invoice_id": invoice.id,
                "invoice_number": invoice.invoice_number,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"])
    def unmatched(self, request):
        qs = self.get_queryset().filter(is_matched=False)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def matched(self, request):
        qs = self.get_queryset().filter(is_matched=True)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)