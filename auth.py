import re
from flask import Blueprint, render_template, request, redirect, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from extensions import db, login_manager, mail
from models import User, Subscription, Invoice
from utils import role_required
from flask import current_app
from flask_mail import Message
from itsdangerous import URLSafeTimedSerializer
from itsdangerous import BadSignature, SignatureExpired

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

def _reset_serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"])


@auth_bp.route("/forgot", methods=["GET", "POST"])
def forgot():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        user = User.query.filter_by(email=email).first()
        if user:
            token = _reset_serializer().dumps(user.email, salt="reset")
            link = request.host_url.rstrip("/") + "/reset/" + token
            try:
                msg = Message("Reset your password", recipients=[user.email])
                msg.body = f"Open this link to reset your password (valid for 1 hour):\n{link}"
                mail.send(msg)
            except Exception as e:
                # Fallback: if email is not configured, print the link in the terminal
                print(f"Email could not be sent ({e}). Reset link: {link}")
        # Same message whether or not the email exists, so people can't discover accounts
        flash("If that email is registered, a reset link has been sent.", "info")
        return redirect("/login")
    return render_template("auth/forgot.html")

@auth_bp.route("/reset/<token>", methods=["GET", "POST"])
def reset(token):
    try:
        email = _reset_serializer().loads(token, salt="reset", max_age=3600)
    except SignatureExpired:
        flash("This reset link has expired. Please request a new one.", "danger")
        return redirect("/forgot")
    except BadSignature:
        flash("This reset link is invalid.", "danger")
        return redirect("/forgot")

    user = User.query.filter_by(email=email).first()
    if not user:
        flash("This reset link is invalid.", "danger")
        return redirect("/forgot")

    if request.method == "POST":
        password = request.form.get("password", "")
        if not PASSWORD_RE.match(password):
            flash("Password must be more than 8 characters and include an uppercase letter, a lowercase letter, and a special character.", "danger")
        else:
            user.password_hash = generate_password_hash(password)
            db.session.commit()
            flash("Password updated. Please log in.", "success")
            return redirect("/login")
    return render_template("auth/reset.html", token=token)

@auth_bp.route("/portal")
@role_required("customer")
def portal():
    # Filter by current_user.id only, never by an id from the URL
    subs = Subscription.query.filter_by(customer_id=current_user.id).all()
    return render_template("portal/index.html", subs=subs)


@auth_bp.route("/portal/invoices")
@role_required("customer")
def portal_invoices():
    page = request.args.get("page", 1, type=int)
    invoices = (
        Invoice.query.filter_by(customer_id=current_user.id)
        .order_by(Invoice.created_at.desc())
        .paginate(page=page, per_page=20, error_out=False)
    )
    return render_template("portal/invoices.html", invoices=invoices)