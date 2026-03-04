# mpesa/views.py

from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
import json

from .models import MpesaTransaction
from .services import process_transaction
from rest_framework.decorators import action
from rest_framework.response import Response
from billing.models import Invoice



@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def mpesa_confirmation(request):
    print("\n🔥🔥🔥 C2B CONFIRMATION RECEIVED 🔥🔥🔥")
    print("DATA:", json.dumps(request.data, indent=2))
    print("🔥🔥🔥 END 🔥🔥🔥\n")

    try:
        receipt = request.data.get("TransID")
        amount = request.data.get("TransAmount")
        phone = request.data.get("MSISDN")
        account_ref = request.data.get("BillRefNumber")

        # Prevent duplicates
        if MpesaTransaction.objects.filter(receipt_number=receipt).exists():
            return Response({"ResultCode": 0, "ResultDesc": "Duplicate ignored"})

        transaction = MpesaTransaction.objects.create(
            receipt_number=receipt,
            phone_number=phone,
            amount=amount,
            account_reference=account_ref,
            raw_payload=request.data
        )

        process_transaction(transaction)

    except Exception as e:
        print("❌ ERROR:", str(e))

    return Response(
        {"ResultCode": 0, "ResultDesc": "Confirmation received"},
        status=status.HTTP_200_OK
    )


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def mpesa_validation(request):
    print("\n🟡 VALIDATION REQUEST:", request.data, "\n")

    return Response(
        {"ResultCode": 0, "ResultDesc": "Accepted"},
        status=status.HTTP_200_OK
    )
    
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .serializers import MpesaTransactionSerializer


class MpesaTransactionViewSet(viewsets.ModelViewSet):
    serializer_class = MpesaTransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return MpesaTransaction.objects.filter(
            property__owner=self.request.user
        ).order_by("-created_at")
        
     

@action(detail=True, methods=["post"])
def manually_allocate(self, request, pk=None):
    transaction = self.get_object()

    if transaction.is_matched:
        return Response({"error": "Already matched."}, status=400)

    invoice_id = request.data.get("invoice_id")

    try:
        invoice = Invoice.objects.get(
            id=invoice_id,
            lease__unit__property__owner=request.user
        )
    except Invoice.DoesNotExist:
        return Response({"error": "Invalid invoice."}, status=400)

    # Apply payment
    invoice.apply_payment(transaction.amount)

    transaction.invoice = invoice
    transaction.tenant = invoice.lease.tenant
    transaction.unit = invoice.lease.unit
    transaction.property = invoice.lease.unit.property
    transaction.is_matched = True
    transaction.is_processed = True
    transaction.save()

    return Response({"message": "Payment manually allocated successfully."})