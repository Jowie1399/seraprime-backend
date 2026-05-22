from decimal import Decimal
from datetime import datetime
import json
from django.db import IntegrityError
from rest_framework import serializers
from django.db import transaction
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
from .services import process_transaction


# =========================
# REGISTER URLS
# =========================
@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def trigger_register_urls(request):
    result = register_c2b_urls()
    return Response(result)


# =========================
# DATE PARSER
# =========================


def parse_mpesa_datetime(value):
    if not value:
        return None

    try:
        # Try M-Pesa format first
        return datetime.strptime(str(value), "%Y%m%d%H%M%S")
    except Exception:
        try:
            # Try ISO format (frontend)
            return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except Exception:
            return None


# =========================
# C2B CONFIRMATION
# =========================
@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def mpesa_confirmation(request):

    print("\n🔥🔥🔥 C2B CONFIRMATION HIT 🔥🔥🔥")

    # SAFE PARSING
    try:
        data = request.data
    except Exception:
        data = json.loads(request.body.decode("utf-8"))

    print("🔥 HEADERS:", request.headers)
    print("🔥 RAW BODY:", request.body)
    print("🔥 PARSED DATA:", data)

    try:
        receipt = data.get("TransID")
        amount = data.get("TransAmount")
        phone = data.get("MSISDN")
        account_ref = data.get("BillRefNumber")
        transaction_date = data.get("TransTime")

        # =========================
        # SAFARICOM TEST PING
        # =========================
        if not receipt:
            print("⚠️ Safaricom test ping received")

            return Response({
                "ResultCode": "0",
                "ResultDesc": "Accepted"
            })

        # =========================
        # NORMALIZE INPUT
        # =========================
        account_ref = str(account_ref or "").strip()
        account_ref = account_ref.replace("-", " ")

        print("RAW BILL REF:", account_ref)

        property_number = None
        unit_part = None

        parts = account_ref.split()

        if len(parts) == 1:
            raw = parts[0]
            property_number = raw

            possible_property = Property.objects.filter(
                property_number=property_number
            ).first()

            if not possible_property and len(raw) > 1:

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

        print("FINAL PROPERTY:", property_number)
        print("FINAL UNIT:", unit_part)

        property_obj = Property.objects.filter(
            property_number=property_number
        ).first()

        if not property_obj:
            print("❌ Property NOT FOUND:", property_number)

            return Response({
                "ResultCode": "0",
                "ResultDesc": "Accepted"
            })

        owner = property_obj.owner

        # =========================
        # UNIT MATCHING
        # =========================
        unit_obj = None

        if unit_part:
            from properties.models import Unit

            unit_obj = Unit.objects.filter(
                Q(name__iexact=unit_part) |
                Q(name__iexact=unit_part.replace(" ", ""))
            ).filter(property=property_obj).first()

            if unit_obj:
                print("✅ Unit matched:", unit_obj.name)
            else:
                print("⚠️ Unit NOT found:", unit_part)

        amount_value = Decimal(str(amount)) if amount else Decimal("0")

        # =========================
        # SAVE TRANSACTION
        # =========================
        try:
            with transaction.atomic():
                transaction_obj = MpesaTransaction.objects.create(
                    owner=owner,
                    receipt_number=str(receipt),
                    phone_number=str(phone or ""),
                    amount=amount_value,
                    account_reference=account_ref,
                    transaction_date=parse_mpesa_datetime(transaction_date),
                    raw_payload=data,
                )

        except IntegrityError:
            print("⚠️ Duplicate receipt:", receipt)

            return Response({
                "ResultCode": "0",
                "ResultDesc": "Accepted"
            })

        print("✅ TRANSACTION SAVED:", transaction_obj.id)

        try:
            process_transaction(transaction_obj)
        except Exception as e:
            print("❌ PROCESSING ERROR:", str(e))

        return Response({
            "ResultCode": "0",
            "ResultDesc": "Accepted"
        })

    except Exception as e:
        print("❌ HARD CRASH:", str(e))

        return Response({
            "ResultCode": "0",
            "ResultDesc": "Accepted"
        })


# =========================
# VALIDATION
# =========================
@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def mpesa_validation(request):

    print("\n🟡 VALIDATION HIT")
    print("DATA:", request.data)

    return Response({
        "ResultCode": "0",
        "ResultDesc": "Accepted"
    })


# =========================
# VIEWSET
# =========================
class MpesaTransactionViewSet(viewsets.ModelViewSet):
    serializer_class = MpesaTransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        return MpesaTransaction.objects.filter(
            owner=user
        ).select_related(
            "property",
            "unit",
            "tenant",
            "invoice",
            "invoice__lease",
            "invoice__lease__tenant",
            "invoice__lease__unit",
            "invoice__lease__unit__property",
        ).order_by("-created_at")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    def perform_create(self, serializer):
        try:
            transaction_obj = serializer.save(owner=self.request.user)
        except IntegrityError:
            raise serializers.ValidationError({
                "receipt_number": "Transaction with this receipt already exists"
            })

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
        transaction = self.get_object()

        invoice_id = request.data.get("invoice_id")

        if not invoice_id:
            return Response({"error": "invoice_id is required"}, status=400)

        try:
            invoice = Invoice.objects.get(
                    id=invoice_id,
                    is_deleted=False,
                    lease__is_active=True,
                    lease__tenant__is_active=True
                )
        except Invoice.DoesNotExist:
            return Response({"error": "Invalid invoice"}, status=404)

        # 🔥 attach invoice FIRST
        transaction.invoice = invoice
        transaction.is_processed = False
        transaction.is_matched = False  # allow processing
        transaction.save()

        # 🔥 THIS IS THE MISSING PIECE
        process_transaction(transaction)

        return Response({"message": "Payment allocated successfully"})

    @action(detail=False, methods=["get"])
    def unmatched(self, request):
        qs = self.get_queryset().filter(is_matched=False)
        return Response(self.get_serializer(qs, many=True).data)

    @action(detail=False, methods=["get"])
    def matched(self, request):
        qs = self.get_queryset().filter(is_matched=True)
        return Response(self.get_serializer(qs, many=True).data)