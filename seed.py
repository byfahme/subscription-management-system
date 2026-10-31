import random
from datetime import date, datetime, time, timedelta
from dateutil.relativedelta import relativedelta
from werkzeug.security import generate_password_hash
from app import app
from extensions import db
from models import (User, Product, Plan, Subscription, SubscriptionLine,
                    Invoice, InvoiceLine, Payment, SUB_STATUSES, INVOICE_STATUSES)

# Test passwords for local demo only
ADMIN_PASSWORD = "Admin@Pass1"
STAFF_PASSWORD = "Staff@Pass1"
CUSTOMER_PASSWORD = "Customer@Pass1"


def seed():
    if User.query.filter_by(email="admin@brightloop.test").first():
        print("Database already seeded. Nothing to do.")
        return

    admin = User(name="Admin", email="admin@brightloop.test",
                 password_hash=generate_password_hash(ADMIN_PASSWORD), role="admin")
    staff = User(name="Staff", email="staff@brightloop.test",
                 password_hash=generate_password_hash(STAFF_PASSWORD), role="staff")
    customers = [
        User(name=f"Customer {i}", email=f"customer{i}@example.com",
             password_hash=generate_password_hash(CUSTOMER_PASSWORD), role="customer")
        for i in range(1, 201)
    ]
    products = [
        Product(name="Odoo Hosting", type="service", sales_price=1000, cost_price=400, tax_percent=18),
        Product(name="Support Pack", type="service", sales_price=250, cost_price=100, tax_percent=18),
    ]
    plan = Plan(name="Monthly Basic", price=1000, period="monthly", min_qty=1,
                start_date=date(2025, 1, 1), end_date=None, auto_close=False,
                allow_pause=True, allow_renew=True, status="active")
    db.session.add_all([admin, staff, plan, *customers, *products])
    db.session.commit()

    subs = []
    for i in range(1, 3001):
        customer = random.choice(customers)
        start = date(2026, 1, 1) + timedelta(days=random.randint(0, 300))
        status = random.choice(SUB_STATUSES)
        sub = Subscription(
            number=f"SUB-{i:04d}", customer_id=customer.id, plan_id=plan.id,
            start_date=start, payment_terms="Net 30", status=status,
            next_billing_date=start + relativedelta(months=1), created_by=admin.id,
        )
        subs.append(sub)
    db.session.add_all(subs)
    db.session.flush()

    invoice_count = 0
    for sub in subs:
        product = random.choice(products)
        line = SubscriptionLine(subscription_id=sub.id, product_id=product.id, variant_id=None,
                                qty=1, unit_price=product.sales_price, tax_percent=product.tax_percent)
        db.session.add(line)
        if sub.status not in ("active", "closed"):
            continue
        invoice_count += 1
        amount = product.sales_price
        tax = amount * product.tax_percent / 100
        total = amount + tax
        inv_status = random.choice(INVOICE_STATUSES)
        invoice = Invoice(
            number=f"INV-{invoice_count:05d}", subscription_id=sub.id, customer_id=sub.customer_id,
            billing_period=sub.start_date.isoformat(), status=inv_status,
            subtotal=amount, tax_total=tax, discount_total=0, total=total,
            due_date=sub.start_date + timedelta(days=30),
            created_at=datetime.combine(sub.start_date, time()),
        )
        db.session.add(invoice)
        db.session.flush()
        db.session.add(InvoiceLine(invoice_id=invoice.id, description=product.name, qty=1,
                                   unit_price=amount, tax_percent=product.tax_percent, amount=total))
        if inv_status == "paid":
            db.session.add(Payment(invoice_id=invoice.id, method="bank", amount=total,
                                   paid_on=sub.start_date, note="Seed data"))
        elif inv_status == "confirmed" and random.random() < 0.5:
            db.session.add(Payment(invoice_id=invoice.id, method="cash", amount=total / 2,
                                   paid_on=sub.start_date, note="Seed partial payment"))

    db.session.commit()
    print(f"Seeded: 1 admin, 1 staff, {len(customers)} customers, {len(subs)} subscriptions, {invoice_count} invoices.")
    print(f"Admin login: admin@brightloop.test / {ADMIN_PASSWORD}")
    print(f"Staff login: staff@brightloop.test / {STAFF_PASSWORD}")


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        seed()