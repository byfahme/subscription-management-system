from flask import Blueprint, render_template, request, redirect, url_for, flash
from extensions import db
from models import Product
from utils import role_required

catalog_bp = Blueprint("catalog", __name__)


@catalog_bp.route("/products")
@role_required("admin", "staff")
def products():
    all_products = Product.query.all()
    return render_template("catalog/products.html", products=all_products)


@catalog_bp.route("/products/new", methods=["GET", "POST"])
@role_required("admin")
def new_product():
    if request.method == "POST":
        product = Product(
            name=request.form["name"],
            type=request.form.get("type", ""),
            sales_price=float(request.form.get("sales_price", 0)),
            cost_price=float(request.form.get("cost_price", 0)),
            tax_percent=float(request.form.get("tax_percent", 0)),
            notes=request.form.get("notes", ""),
        )
        db.session.add(product)
        db.session.commit()
        flash("Product added.", "success")
        return redirect(url_for("catalog.products"))
    return render_template("catalog/new_product.html")
