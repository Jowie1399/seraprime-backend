from rest_framework.decorators import api_view, permission_classes, authentication_classes, action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status, viewsets

from django.db import transaction, IntegrityError

from decimal import Decimal
import json

from .models import MpesaTransaction
from .services import process_transaction
from .serializers import MpesaTransactionSerializer
from billing.models import Invoice


# ==============================
# M-PESA CONFIRMATION CALLBACK
# ==============================

@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def mpesa_confirmation(request):

    # Debug log (safe)
    print("\n🔥 C2B CONFIRMATION RECEIVED 🔥")

    receipt = request.data.get("TransID")
    amount = request.data.get("TransAmount")
    phone = request.data.get("MSISDN")
    account_ref = request.data.get("BillRefNumber")

    if not receipt:
        return Response(
            {"ResultCode": 1, "ResultDesc": "Invalid receipt"},
            status=status.HTTP_200_OK
        )

    try:

        amount_value = Decimal(str(amount)) if amount else Decimal("0")

        with transaction.atomic():

            transaction_obj = MpesaTransaction.objects.create(
                receipt_number=receipt,
                phone_number=phone,
                amount=amount_value,
                account_reference=account_ref,
                raw_payload=request.data,
            )

    except IntegrityError:
        # Duplicate transaction (Mpesa sometimes retries callbacks)
        return Response(
            {"ResultCode": 0, "ResultDesc": "Duplicate ignored"},
            status=status.HTTP_200_OK
        )

    except Exception as e:
        print("❌ DB ERROR:", str(e))
        return Response(
            {"ResultCode": 0, "ResultDesc": "Accepted"},
            status=status.HTTP_200_OK
        )

    # Process outside DB creation transaction
    try:
        process_transaction(transaction_obj)
    except Exception as e:
        # Do not fail Mpesa response if internal processing fails
        print("❌ PROCESSING ERROR:", str(e))

    return Response(
        {"ResultCode": 0, "ResultDesc": "Confirmation received"},
        status=status.HTTP_200_OK
    )


# ==============================
# M-PESA VALIDATION CALLBACK
# ==============================

@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def mpesa_validation(request):

    print("\n🟡 VALIDATION REQUEST RECEIVED")

    # Always accept payment (unless you implement validation rules)
    return Response(
        {"ResultCode": 0, "ResultDesc": "Accepted"},
        status=status.HTTP_200_OK,
    )


# ==============================
# TRANSACTION VIEWSET
# ==============================

class MpesaTransactionViewSet(viewsets.ModelViewSet):

    serializer_class = MpesaTransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):

        return (
            MpesaTransaction.objects
            .filter(property__owner=self.request.user)
            .select_related(
                "property",
                "unit",
                "tenant",
                "invoice"
            )
            .order_by("-created_at")
        )

    def perform_create(self, serializer):
        """
        Used when importing past Mpesa transactions
        """

        transaction_obj = serializer.save()

        try:
            process_transaction(transaction_obj)
        except Exception as e:
            print("❌ Import processing error:", str(e))


    # ==============================
    # MANUAL PAYMENT ALLOCATION
    # ==============================

    @action(detail=True, methods=["post"])
    def manually_allocate(self, request, pk=None):

        with transaction.atomic():

            transaction_obj = (
                MpesaTransaction.objects
                .select_for_update()
                .get(pk=pk)
            )

            if transaction_obj.is_matched:
                return Response(
                    {"error": "Transaction already matched."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            invoice_id = request.data.get("invoice_id")

            try:

                invoice = (
                    Invoice.objects
                    .select_for_update()
                    .get(
                        id=invoice_id,
                        lease__unit__property__owner=request.user
                    )
                )

            except Invoice.DoesNotExist:

                return Response(
                    {"error": "Invalid invoice."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Apply payment safely
            invoice.apply_payment(transaction_obj.amount)

            transaction_obj.invoice = invoice
            transaction_obj.tenant = invoice.lease.tenant
            transaction_obj.unit = invoice.lease.unit
            transaction_obj.property = invoice.lease.unit.property

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
            {"message": "Payment allocated successfully"},
            status=status.HTTP_200_OK
        )