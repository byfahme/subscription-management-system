from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from flask import Blueprint, redirect, flash
from sqlalchemy.exc import IntegrityError

from extensions import db
from models import (Subscription, SubscriptionLine, Plan,
                    Discount, Invoice, InvoiceLine)

# utils.py is not pushed yet, so use a temporary version if it is missing
try:
    from utils import role_required
except ImportError:
    from functools import wraps
    from flask import abort
    from flask_login import current_user

    def role_required(*roles):
        def deco(f):
            @wraps(f)
            def wrapper(*args, **kwargs):
                if (not current_user.is_authenticated
                        or current_user.role not in roles):
                    abort(403)
                return f(*args, **kwargs)
            return wrapper
        return deco

billing_bp = Blueprint("billing", __name__)


def next_date(d, period):
    if period == "daily":
        return d + relativedelta(days=1)
    if period == "weekly":
        return d + relativedelta(weeks=1)
    if period == "monthly":
        return d + relativedelta(months=1)
    if period == "yearly":
        return d + relativedelta(years=1)
    raise ValueError("Unknown period")


def find_discount(sub, lines, subtotal):
    today = date.today()
    total_qty = sum(l.qty for l in lines)
    product_ids = [l.product_id for l in lines]
    for d in Discount.query.all():
        if d.start_date and d.start_date > today:
            continue
        if d.end_date and d.end_date < today:
            continue
        if d.usage_limit is not None and (d.times_used or 0) >= d.usage_limit:
            continue
        if d.min_amount and subtotal < d.min_amount:
            continue
        if d.min_qty and total_qty < d.min_qty:
            continue
        if d.subscription_id and d.subscription_id != sub.id:
            continue
        if d.product_id and d.product_id not in product_ids:
            continue
        return d
    return None


@billing_bp.route("/billing/run", methods=["POST"])
@role_required("admin")
def billing_run():
    today = date.today()
    subs = Subscription.query.filter(
        Subscription.status == "active",
        Subscription.next_billing_date <= today,
    ).all()

    created = 0
    skipped = 0

    for sub in subs:
        try:
            plan = Plan.query.get(sub.plan_id)
            lines = SubscriptionLine.query.filter_by(
                subscription_id=sub.id).all()

            subtotal = 0
            tax_total = 0
            for l in lines:
                amount = l.qty * l.unit_price
                subtotal += amount
                tax_total += amount * (l.tax_percent or 0) / 100

            discount_total = 0
            disc = find_discount(sub, lines, subtotal)
            if disc:
                if disc.type == "percent":
                    discount_total = subtotal * disc.value / 100
                else:
                    discount_total = disc.value
                discount_total = min(discount_total, subtotal)
                disc.times_used = (disc.times_used or 0) + 1

            invoice = Invoice(
                number=f"INV-{Invoice.query.count() + 1:04d}",
                subscription_id=sub.id,
                customer_id=sub.customer_id,
                billing_period=str(sub.next_billing_date),
                status="draft",
                subtotal=subtotal,
                tax_total=tax_total,
                discount_total=discount_total,
                total=subtotal + tax_total - discount_total,
                due_date=today + timedelta(days=30),
            )
            db.session.add(invoice)
            db.session.flush()

            for l in lines:
                db.session.add(InvoiceLine(
                    invoice_id=invoice.id,
                    description=f"Product {l.product_id}",
                    qty=l.qty,
                    unit_price=l.unit_price,
                    tax_percent=l.tax_percent,
                    amount=l.qty * l.unit_price,
                ))

            sub.next_billing_date = next_date(
                sub.next_billing_date, plan.period)

            db.session.commit()
            created += 1
        except IntegrityError:
            db.session.rollback()
            skipped += 1

    flash(f"{created} created, {skipped} skipped", "success")
    return redirect("/invoices")