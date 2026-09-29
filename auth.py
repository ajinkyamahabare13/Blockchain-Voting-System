from functools import wraps

from flask import (
    session,
    flash,
    redirect
)

from models import User, db


def login_required(view_function):

    @wraps(view_function)
    def wrapped_view(*args, **kwargs):

        if "user_id" not in session:

            flash(
                "Please login first.",
                "warning"
            )

            return redirect("/login")

        return view_function(
            *args,
            **kwargs
        )

    return wrapped_view


def admin_required(view_function):

    @wraps(view_function)
    def wrapped_view(*args, **kwargs):

        if "user_id" not in session:

            flash(
                "Please login first.",
                "warning"
            )

            return redirect("/login")

        user = db.session.get(
        User,
        session["user_id"]
       ) 

        if user is None:

            session.clear()

            flash(
                "User account not found.",
                "danger"
            )

            return redirect("/login")

        if not user.is_admin:

            flash(
                "Access Denied! Admins only.",
                "danger"
            )

            return redirect("/dashboard")

        return view_function(
            *args,
            **kwargs
        )

    return wrapped_view