from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from flask import Blueprint, redirect, flash
from sqlalchemy.exc import IntegrityError

from extensions import db
from models import (
    Subscription, SubscriptionLine, Plan,
    Discount, Invoice, InvoiceLine
)
from flask import render_template, abort, request
from flask_login import current_user
from models import Payment, User, INVOICE_STATUSES

from utils import role_required

billing_bp = Blueprint("billing", __name__)

def invoice_money(inv):
    payments = Payment.query.filter_by(invoice_id=inv.id).all()
    paid = round(sum(p.amount or 0 for p in payments), 2)
    outstanding = round(max((inv.total or 0) - paid, 0), 2)
    overdue = bool(
        inv.status == "confirmed"
        and inv.due_date
        and inv.due_date < date.today()
        and outstanding > 0
    )
    return paid, outstanding, overdue


def can_view_invoice(inv):
    if current_user.role in ("admin", "staff"):
        return True
    return inv.customer_id == current_user.id


@billing_bp.route("/invoices")
@role_required("admin", "staff", "customer")
def invoice_list():
    query = Invoice.query
    if current_user.role == "customer":
        query = query.filter_by(customer_id=current_user.id)

    status = request.args.get("status", "")
    customer_id = request.args.get("customer_id", type=int)
    if status:
        query = query.filter_by(status=status)
    if customer_id and current_user.role != "customer":
        query = query.filter_by(customer_id=customer_id)

    invoices = query.order_by(Invoice.id.desc()).all()

    ids = {i.customer_id for i in invoices}
    names = {}
    if ids:
        names = {u.id: u.name for u in User.query.filter(User.id.in_(ids)).all()}

    rows = []
    for inv in invoices:
        paid, outstanding, overdue = invoice_money(inv)
        rows.append({
            "inv": inv,
            "customer": names.get(inv.customer_id, "-"),
            "paid": paid,
            "outstanding": outstanding,
            "overdue": overdue,
        })

    customers = []
    if current_user.role in ("admin", "staff"):
        customers = User.query.filter_by(role="customer").all()

    return render_template(
        "billing/invoices.html",
        rows=rows,
        statuses=INVOICE_STATUSES,
        status=status,
        customers=customers,
        customer_id=customer_id,
    )


@billing_bp.route("/invoices/<int:invoice_id>")
@role_required("admin", "staff", "customer")
def invoice_detail(invoice_id):
    inv = Invoice.query.get_or_404(invoice_id)
    if not can_view_invoice(inv):
        abort(403)

    lines = InvoiceLine.query.filter_by(invoice_id=inv.id).all()
    payments = Payment.query.filter_by(invoice_id=inv.id).all()
    customer = db.session.get(User, inv.customer_id)
    paid, outstanding, overdue = invoice_money(inv)

    return render_template(
        "billing/invoice_detail.html",
        inv=inv,
        lines=lines,
        payments=payments,
        customer=customer,
        paid=paid,
        outstanding=outstanding,
        overdue=overdue,
    )