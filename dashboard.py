from datetime import date
from flask import Blueprint, render_template, request
from sqlalchemy import func, or_
from extensions import db
from models import Subscription, Invoice, Payment, User
from utils import role_required

dashboard_bp = Blueprint("dashboard", __name__)

PER_PAGE = 20


def _parse_date(value):
    try:
        return date.fromisoformat(value) if value else None
    except ValueError:
        return None


def _filter_payments(query, start, end):
    if start:
        query = query.filter(Payment.paid_on >= start)
    if end:
        query = query.filter(Payment.paid_on <= end)
    return query


def _filter_customer(query, text):
    if text:
        like = f"%{text}%"
        query = query.filter(or_(User.name.ilike(like), User.email.ilike(like)))
    return query


@dashboard_bp.route("/dashboard")
@role_required("admin", "staff")
def dashboard():
    today = date.today()
    start = _parse_date(request.args.get("start"))
    end = _parse_date(request.args.get("end"))
    status = request.args.get("status", "")
    customer_text = request.args.get("customer", "").strip()

    # Summary numbers, all calculated by SQL
    active_count = (
        db.session.query(func.count(Subscription.id))
        .filter(Subscription.status == "active")
        .scalar()
    )
    collected = _filter_payments(
        db.session.query(func.coalesce(func.sum(Payment.amount), 0)), start, end
    ).scalar()

    billed = (
        db.session.query(func.coalesce(func.sum(Invoice.total), 0))
        .filter(Invoice.status == "confirmed")
        .scalar()
    )
    paid_on_confirmed = (
        db.session.query(func.coalesce(func.sum(Payment.amount), 0))
        .join(Invoice, Payment.invoice_id == Invoice.id)
        .filter(Invoice.status == "confirmed")
        .scalar()
    )
    outstanding = billed - paid_on_confirmed

    # Total paid per invoice, used to find overdue invoices
    paid_per_invoice = (
        db.session.query(Payment.invoice_id.label("invoice_id"),
                         func.sum(Payment.amount).label("paid"))
        .group_by(Payment.invoice_id)
        .subquery()
    )
    overdue_query = (
        db.session.query(Invoice, User)
        .join(User, Invoice.customer_id == User.id)
        .outerjoin(paid_per_invoice, Invoice.id == paid_per_invoice.c.invoice_id)
        .filter(Invoice.status == "confirmed")
        .filter(Invoice.due_date < today)
        .filter(Invoice.total > func.coalesce(paid_per_invoice.c.paid, 0))
    )
    overdue_query = _filter_customer(overdue_query, customer_text)
    overdue = overdue_query.order_by(Invoice.due_date).paginate(
        page=request.args.get("overdue_page", 1, type=int), per_page=PER_PAGE, error_out=False
    )

    # Filterable invoice list
    invoice_query = db.session.query(Invoice, User).join(User, Invoice.customer_id == User.id)
    if status:
        invoice_query = invoice_query.filter(Invoice.status == status)
    if start:
        invoice_query = invoice_query.filter(Invoice.created_at >= start)
    if end:
        invoice_query = invoice_query.filter(Invoice.created_at <= end)
    invoice_query = _filter_customer(invoice_query, customer_text)
    invoices = invoice_query.order_by(Invoice.created_at.desc()).paginate(
        page=request.args.get("page", 1, type=int), per_page=PER_PAGE, error_out=False
    )

    # Monthly revenue for the chart
    month = func.strftime("%Y-%m", Payment.paid_on)
    monthly = _filter_payments(
        db.session.query(month.label("month"), func.sum(Payment.amount)), start, end
    ).group_by("month").order_by("month").all()
    chart_labels = [row[0] for row in monthly]
    chart_values = [float(row[1]) for row in monthly]

    return render_template(
        "dashboard/index.html",
        active_count=active_count,
        collected=collected,
        outstanding=outstanding,
        overdue=overdue,
        invoices=invoices,
        chart_labels=chart_labels,
        chart_values=chart_values,
        filters={"start": request.args.get("start", ""), "end": request.args.get("end", ""),
                 "status": status, "customer": customer_text},
    )