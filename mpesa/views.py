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
from properties.models import Property
from .daraja import register_c2b_urls


# ✅ REGISTER URL TRIGGER
@api_view(["GET"])
def trigger_register_urls(request):
    result = register_c2b_urls()
    return Response(result)


def parse_mpesa_datetime(value):
    if not value:
        return None
    try:
        return datetime.strptime(str(value), "%Y%m%d%H%M%S")
    except Exception:
        return None


# ✅ M-PESA CONFIRMATION (PRODUCTION LOGIC)
@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def mpesa_confirmation(request):
    print("\n🔥 C2B CONFIRMATION RECEIVED 🔥")
    print("DATA:", request.data)

    receipt = request.data.get("TransID")
    amount = request.data.get("TransAmount")
    phone = request.data.get("MSISDN")
    account_ref = request.data.get("BillRefNumber")  # 👈 THIS IS KEY
    transaction_date = request.data.get("TransTime")

    if not receipt:
        return Response(
            {"ResultCode": 1, "ResultDesc": "Invalid receipt"},
            status=status.HTTP_200_OK,
        )

    try:
        amount_value = Decimal(str(amount)) if amount else Decimal("0")

        # ✅ REAL LOGIC: Map payment → Property → Owner
        property_obj = Property.objects.filter(
            property_number=account_ref
        ).first()

        if not property_obj:
            print("❌ Property not found for:", account_ref)
            return Response(
                {"ResultCode": 0, "ResultDesc": "Property not found"},
                status=status.HTTP_200_OK,
            )

        owner = property_obj.owner

        with transaction.atomic():
            transaction_obj = MpesaTransaction.objects.create(
                owner=owner,
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

    # ✅ Process payment (match to invoice)
    try:
        process_transaction(transaction_obj)
    except Exception as e:
        print("❌ PROCESSING ERROR:", str(e))

    return Response(
        {"ResultCode": 0, "ResultDesc": "Confirmation received"},
        status=status.HTTP_200_OK,
    )


# ✅ VALIDATION
@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def mpesa_validation(request):
    print("\n🟡 VALIDATION REQUEST RECEIVED")
    print("DATA:", request.data)

    return Response(
        {"ResultCode": 0, "ResultDesc": "Accepted"},
        status=status.HTTP_200_OK,
    )


# ✅ VIEWSET
class MpesaTransactionViewSet(viewsets.ModelViewSet):
    serializer_class = MpesaTransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        return (
            MpesaTransaction.objects
            .filter(owner=user)
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
            .order_by("-created_at")
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    # ✅ Manual create
    def perform_create(self, serializer):
        transaction_obj = serializer.save(owner=self.request.user)

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

    # ✅ Manual allocation
    @action(detail=True, methods=["post"])
    def manually_allocate(self, request, pk=None):
        with transaction.atomic():
            transaction_obj = self.get_queryset().select_for_update().get(pk=pk)

            if transaction_obj.is_matched:
                return Response(
                    {"error": "Already matched"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            invoice_id = request.data.get("invoice_id")

            if not invoice_id:
                return Response(
                    {"error": "invoice_id required"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            try:
                invoice = Invoice.objects.get(
                    id=invoice_id,
                    lease__unit__property__owner=request.user
                )
            except Invoice.DoesNotExist:
                return Response(
                    {"error": "Invalid invoice"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if invoice.status == "paid":
                return Response(
                    {"error": "Invoice already paid"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            invoice.apply_payment(transaction_obj.amount)

            transaction_obj.invoice = invoice
            transaction_obj.tenant = invoice.lease.tenant
            transaction_obj.unit = invoice.lease.unit
            transaction_obj.property = invoice.lease.unit.property
            transaction_obj.is_matched = True
            transaction_obj.is_processed = True
            transaction_obj.save()

        return Response({
            "message": "Payment allocated successfully"
        })

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