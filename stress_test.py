# stress_test.py
from properties.models import Property, Unit, Tenant, Lease
from billing.models import Invoice, Receipt
from django.contrib.auth import get_user_model
from decimal import Decimal
from datetime import date, timedelta
import random

# ==== CONFIG ====
PROPERTY_NUMBER = "5001"
PROPERTY_NAME = "Stress Test Property"
PROPERTY_LOCATION = "Nairobi"
TENANTS_COUNT = 150
RENT_AMOUNT = Decimal("10000.00")
MAX_WALLET = 15000
INVOICE_DAYS = 30

User = get_user_model()
owner = User.objects.get(username="landlady")

# ==== 1. Create property ====
property1, _ = Property.objects.get_or_create(
    property_number=PROPERTY_NUMBER,
    defaults={
        "owner": owner,
        "name": PROPERTY_NAME,
        "location": PROPERTY_LOCATION,
    }
)

# ==== 2. Clear existing data ====
property1.units.all().delete()
property1.tenants.all().delete()
Lease.objects.filter(unit__property=property1).delete()
Invoice.objects.filter(lease__unit__property=property1).delete()
Receipt.objects.filter(invoice__lease__unit__property=property1).delete()

# ==== 3. Create units, tenants, leases ====
units = []
tenants = []

for i in range(1, TENANTS_COUNT + 1):
    unit = Unit.objects.create(property=property1, name=f"Unit {i}")
    units.append(unit)
    wallet_balance = Decimal(random.randint(0, MAX_WALLET))
    tenant = Tenant.objects.create(
        property=property1,
        full_name=f"Tenant {i}",
        phone=f"0711{random.randint(100000, 999999)}",
        wallet_balance=wallet_balance
    )
    tenants.append(tenant)
    Lease.objects.create(
        unit=unit,
        tenant=tenant,
        rent_amount=RENT_AMOUNT,
        start_date=date.today(),
        is_active=True
    )

print(f"Leases created: {Lease.objects.filter(unit__property=property1).count()}")

# ==== 4. Create invoices ====
invoices = []
for tenant in tenants:
    lease = tenant.leases.first()
    invoice = Invoice.objects.create(
        lease=lease,
        amount=RENT_AMOUNT,
        due_date=date.today() + timedelta(days=INVOICE_DAYS)
    )
    # Apply tenant wallet automatically
    invoice.apply_wallet()
    invoices.append(invoice)

print(f"Invoices created: {Invoice.objects.filter(lease__unit__property=property1).count()}")

# ==== 5. Generate random receipts and suspense ====
suspense_transactions = []

for invoice in invoices:
    if invoice.status == "paid":
        continue  # Skip fully paid

    r = random.random()

    if r < 0.25:
        # Full payment
        Receipt.objects.create(invoice=invoice, amount_paid=invoice.balance())
    elif r < 0.50:
        # Partial payment
        partial_amount = Decimal(random.randint(2000, min(8000, int(invoice.balance()))))
        Receipt.objects.create(invoice=invoice, amount_paid=partial_amount)
    elif r < 0.75:
        # Overpayment (adds to wallet)
        over_amount = Decimal(random.randint(int(invoice.balance()) + 1000, int(invoice.balance()) + 5000))
        Receipt.objects.create(invoice=invoice, amount_paid=over_amount)
    else:
        # Wrong reference / suspense
        suspense_transactions.append(invoice.id)

# ==== 6. Summary ====
print("=== Stress Test Summary ===")
print("Receipts created:", Receipt.objects.filter(invoice__lease__unit__property=property1).count())
print("Suspense transactions:", len(suspense_transactions))
print("Paid:", Invoice.objects.filter(status="paid", lease__unit__property=property1).count())
print("Partial:", Invoice.objects.filter(status="partial", lease__unit__property=property1).count())
print("Unpaid:", Invoice.objects.filter(status="unpaid", lease__unit__property=property1).count())
print("Past Due:", Invoice.objects.filter(status="past_due", lease__unit__property=property1).count())
