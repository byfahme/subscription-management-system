from functools import wraps
from flask import abort
from flask_login import current_user, login_required


def role_required(*roles):
    """Use on a route like: @role_required("admin", "staff")"""
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapper(*args, **kwargs):
            if current_user.role not in roles:
                abort(403)  # wrong role: show "Forbidden"
            return view(*args, **kwargs)
        return wrapper
    return decorator
