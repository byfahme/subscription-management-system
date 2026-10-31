from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, flash
from extensions import db
from models import (Product, Plan, QuotationTemplate, QuotationTemplateLine,
                    Subscription, SubscriptionLine, User)
from utils import role_required
from services import change_subscription_status

catalog_bp = Blueprint("catalog", __name__)


# ---------- PRODUCTS ----------

@catalog_bp.route("/products")
@role_required("admin", "staff")
def products():
    return render_template("catalog/products.html", products=Product.query.all())


@catalog_bp.route("/products/new", methods=["GET", "POST"])
@role_required("admin")
def new_product():
    if request.method == "POST":
        db.session.add(Product(
            name=request.form["name"],
            type=request.form.get("type", ""),
            sales_price=float(request.form.get("sales_price", 0)),
            cost_price=float(request.form.get("cost_price", 0)),
            tax_percent=float(request.form.get("tax_percent", 0)),
            notes=request.form.get("notes", ""),
        ))
        db.session.commit()
        flash("Product added.", "success")
        return redirect(url_for("catalog.products"))
    return render_template("catalog/new_product.html")


# ---------- PLANS ----------

@catalog_bp.route("/plans")
@role_required("admin", "staff")
def plans():
    # Auto-close plans whose end date has passed
    for p in Plan.query.all():
        if p.auto_close and p.end_date and p.end_date < date.today() and p.status != "closed":
            p.status = "closed"
    db.session.commit()
    return render_template("catalog/plans.html", plans=Plan.query.all())


@catalog_bp.route("/plans/new", methods=["GET", "POST"])
@role_required("admin")
def new_plan():
    if request.method == "POST":
        f = request.form
        db.session.add(Plan(
            name=f["name"],
            price=float(f.get("price", 0)),
            period=f.get("period", "monthly"),
            min_qty=int(f.get("min_qty", 1)),
            start_date=date.fromisoformat(
                f["start_date"]) if f.get("start_date") else None,
            end_date=date.fromisoformat(
                f["end_date"]) if f.get("end_date") else None,
            auto_close=bool(f.get("auto_close")),
            allow_pause=bool(f.get("allow_pause")),
            allow_renew=bool(f.get("allow_renew")),
            status="active",
        ))
        db.session.commit()
        flash("Plan created.", "success")
        return redirect(url_for("catalog.plans"))
    return render_template("catalog/new_plan.html")


@catalog_bp.route("/plans/<int:plan_id>/<action>", methods=["POST"])
@role_required("admin")
def plan_action(plan_id, action):
    plan = db.session.get(Plan, plan_id)
    if action == "pause" and plan.allow_pause:
        plan.status = "paused"
    elif action == "renew" and plan.allow_renew:
        plan.status = "active"
    elif action == "close":
        plan.status = "closed"
    else:
        flash("That action is not allowed for this plan.", "danger")
        return redirect(url_for("catalog.plans"))
    db.session.commit()
    flash(f"Plan {action}d.", "success")
    return redirect(url_for("catalog.plans"))


# ---------- QUOTATION TEMPLATES ----------

@catalog_bp.route("/templates")
@role_required("admin", "staff")
def templates():
    return render_template("catalog/templates.html",
                           templates=QuotationTemplate.query.all())


@catalog_bp.route("/templates/new", methods=["GET", "POST"])
@role_required("admin")
def new_template():
    if request.method == "POST":
        f = request.form
        tpl = QuotationTemplate(
            name=f["name"],
            plan_id=int(f["plan_id"]) if f.get("plan_id") else None,
            validity_days=int(f.get("validity_days", 30)),
        )
        db.session.add(tpl)
        db.session.flush()  # gives tpl.id before we add the line
        db.session.add(QuotationTemplateLine(
            template_id=tpl.id,
            product_id=int(f["product_id"]),
            qty=int(f.get("qty", 1)),
        ))
        db.session.commit()
        flash("Template created.", "success")
        return redirect(url_for("catalog.templates"))
    return render_template("catalog/new_template.html",
                           plans=Plan.query.all(), products=Product.query.all())


# ---------- SUBSCRIPTIONS ----------

@catalog_bp.route("/subscriptions")
@role_required("admin", "staff")
def subscriptions():
    return render_template("catalog/subscriptions.html",
                           subs=Subscription.query.order_by(Subscription.id.desc()).all())


@catalog_bp.route("/subscriptions/new", methods=["GET", "POST"])
@role_required("admin", "staff")
def new_subscription():
    if request.method == "POST":
        f = request.form
        count = Subscription.query.count() + 1
        sub = Subscription(
            number=f"SUB-{count:04d}",
            customer_id=int(f["customer_id"]),
            plan_id=int(f["plan_id"]) if f.get("plan_id") else None,
            start_date=date.fromisoformat(f["start_date"]),
            expiry_date=date.fromisoformat(
                f["expiry_date"]) if f.get("expiry_date") else None,
            payment_terms=f.get("payment_terms", "Net 30"),
            status="draft",
            next_billing_date=None,
            created_by=None,
        )
        db.session.add(sub)
        db.session.flush()
        product = db.session.get(Product, int(f["product_id"]))
        db.session.add(SubscriptionLine(
            subscription_id=sub.id,
            product_id=product.id,
            qty=int(f.get("qty", 1)),
            unit_price=product.sales_price,
            tax_percent=product.tax_percent,
        ))
        db.session.commit()
        flash(f"Subscription {sub.number} created.", "success")
        return redirect(url_for("catalog.subscription_detail", sub_id=sub.id))
    return render_template("catalog/new_subscription.html",
                           customers=User.query.filter_by(
                               role="customer").all(),
                           plans=Plan.query.all(),
                           products=Product.query.all())


@catalog_bp.route("/subscriptions/<int:sub_id>")
@role_required("admin", "staff")
def subscription_detail(sub_id):
    sub = db.session.get(Subscription, sub_id)
    return render_template("catalog/subscription_detail.html", sub=sub)


@catalog_bp.route("/subscriptions/<int:sub_id>/status", methods=["POST"])
@role_required("admin", "staff")
def change_status(sub_id):
    sub = db.session.get(Subscription, sub_id)
    try:
        change_subscription_status(sub, request.form["new_status"])
        db.session.commit()
        flash(f"Status changed to {sub.status}.", "success")
    except ValueError as e:
        db.session.rollback()
        flash(str(e), "danger")
    return redirect(url_for("catalog.subscription_detail", sub_id=sub.id))
