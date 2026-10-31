from datetime import datetime
from flask_login import UserMixin
from extensions import db

ROLES = ["admin", "staff", "customer"]
SUB_STATUSES = ["draft", "quotation", "confirmed", "active", "closed"]
INVOICE_STATUSES = ["draft", "confirmed", "paid", "cancelled"]
PERIODS = ["daily", "weekly", "monthly", "yearly"]


class User(UserMixin, db.Model):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="customer")
    reset_token = db.Column(db.String(256))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Product(db.Model):
    __tablename__ = "product"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    type = db.Column(db.String(60))
    sales_price = db.Column(db.Float, default=0)
    cost_price = db.Column(db.Float, default=0)
    notes = db.Column(db.Text)
    tax_percent = db.Column(db.Float, default=0)


class Variant(db.Model):
    __tablename__ = "variant"
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    extra_price = db.Column(db.Float, default=0)


class Plan(db.Model):
    __tablename__ = "plan"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    price = db.Column(db.Float, default=0)
    period = db.Column(db.String(20), default="monthly")
    min_qty = db.Column(db.Integer, default=1)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    auto_close = db.Column(db.Boolean, default=False)
    allow_pause = db.Column(db.Boolean, default=False)
    allow_renew = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(20), default="active")


class QuotationTemplate(db.Model):
    __tablename__ = "quotation_template"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    plan_id = db.Column(db.Integer, db.ForeignKey("plan.id"))
    validity_days = db.Column(db.Integer, default=30)


class QuotationTemplateLine(db.Model):
    __tablename__ = "quotation_template_line"
    id = db.Column(db.Integer, primary_key=True)
    template_id = db.Column(db.Integer, db.ForeignKey("quotation_template.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)
    variant_id = db.Column(db.Integer, db.ForeignKey("variant.id"))
    qty = db.Column(db.Integer, default=1)


class Subscription(db.Model):
    __tablename__ = "subscription"
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(20), unique=True, nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    plan_id = db.Column(db.Integer, db.ForeignKey("plan.id"))
    start_date = db.Column(db.Date)
    expiry_date = db.Column(db.Date)
    payment_terms = db.Column(db.String(60))
    status = db.Column(db.String(20), default="draft", index=True)
    next_billing_date = db.Column(db.Date, index=True)
    created_by = db.Column(db.Integer, db.ForeignKey("user.id"))


class SubscriptionLine(db.Model):
    __tablename__ = "subscription_line"
    id = db.Column(db.Integer, primary_key=True)
    subscription_id = db.Column(db.Integer, db.ForeignKey("subscription.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)
    variant_id = db.Column(db.Integer, db.ForeignKey("variant.id"))
    qty = db.Column(db.Integer, default=1)
    unit_price = db.Column(db.Float, default=0)
    tax_percent = db.Column(db.Float, default=0)


class Discount(db.Model):
    __tablename__ = "discount"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    type = db.Column(db.String(10), nullable=False)  # "fixed" or "percent"
    value = db.Column(db.Float, default=0)
    min_amount = db.Column(db.Float, default=0)
    min_qty = db.Column(db.Integer, default=0)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    usage_limit = db.Column(db.Integer)
    times_used = db.Column(db.Integer, default=0)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"))
    subscription_id = db.Column(db.Integer, db.ForeignKey("subscription.id"))


class Invoice(db.Model):
    __tablename__ = "invoice"
    __table_args__ = (
        db.UniqueConstraint("subscription_id", "billing_period"),  # prevents double billing
    )
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(20), unique=True, nullable=False)
    subscription_id = db.Column(db.Integer, db.ForeignKey("subscription.id"), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    billing_period = db.Column(db.String(10), nullable=False)  # ISO date string
    status = db.Column(db.String(20), default="draft", index=True)
    subtotal = db.Column(db.Float, default=0)
    tax_total = db.Column(db.Float, default=0)
    discount_total = db.Column(db.Float, default=0)
    total = db.Column(db.Float, default=0)
    due_date = db.Column(db.Date, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class InvoiceLine(db.Model):
    __tablename__ = "invoice_line"
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey("invoice.id"), nullable=False)
    description = db.Column(db.String(200))
    qty = db.Column(db.Integer, default=1)
    unit_price = db.Column(db.Float, default=0)
    tax_percent = db.Column(db.Float, default=0)
    amount = db.Column(db.Float, default=0)


class Payment(db.Model):
    __tablename__ = "payment"
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey("invoice.id"), nullable=False, index=True)
    method = db.Column(db.String(30))
    amount = db.Column(db.Float, nullable=False)
    paid_on = db.Column(db.Date)
    note = db.Column(db.Text)