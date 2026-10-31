from functools import wraps

from flask import abort, current_app
from flask_login import current_user


def role_required(*roles):
    """Use on a route like: @role_required("admin", "staff")"""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                return current_app.login_manager.unauthorized()
            if current_user.role not in roles:
                abort(403)
            return f(*args, **kwargs)
        return wrapper
    return decorator
