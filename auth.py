import re
from flask import Blueprint, render_template, request, redirect, flash
from flask_login import login_user, logout_user, login_required
from werkzeug.security import check_password_hash, generate_password_hash
from extensions import db, login_manager
from models import User
from utils import role_required

auth_bp = Blueprint("auth", __name__)

# More than 8 characters, with at least one lowercase, one uppercase, and one special character
PASSWORD_RE = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*[^A-Za-z0-9]).{9,}$")


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email:
            flash("Name and email are required.", "danger")
        elif not PASSWORD_RE.match(password):
            flash("Password must be more than 8 characters and include an uppercase letter, a lowercase letter, and a special character.", "danger")
        elif User.query.filter_by(email=email).first():
            flash("An account with this email already exists.", "danger")
        else:
            user = User(
                name=name,
                email=email,
                password_hash=generate_password_hash(password),
                role="customer",  # public signup can never create admin or staff
            )
            db.session.add(user)
            db.session.commit()
            flash("Account created. Please log in.", "success")
            return redirect("/login")
    return render_template("auth/register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            if user.role == "customer":
                return redirect("/portal")
            return redirect("/dashboard")
        flash("Wrong email or password.", "danger")
    return render_template("auth/login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect("/login")

@auth_bp.route("/admin/staff/new", methods=["GET", "POST"])
@role_required("admin")
def add_staff():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email:
            flash("Name and email are required.", "danger")
        elif not PASSWORD_RE.match(password):
            flash("Password must be more than 8 characters and include an uppercase letter, a lowercase letter, and a special character.", "danger")
        elif User.query.filter_by(email=email).first():
            flash("An account with this email already exists.", "danger")
        else:
            staff = User(
                name=name,
                email=email,
                password_hash=generate_password_hash(password),
                role="staff",  # only admins can reach this page, so staff is set here
            )
            db.session.add(staff)
            db.session.commit()
            flash(f"Staff account created for {email}.", "success")
            return redirect("/admin/staff/new")
    return render_template("auth/add_staff.html")