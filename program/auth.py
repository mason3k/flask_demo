import functools

from flask import (
    Blueprint,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import select
from werkzeug.security import check_password_hash, generate_password_hash

from . import db
from .models import User

bp = Blueprint("auth", __name__, url_prefix="/auth")


class InputError(Exception):
    ...


@bp.route("/register", methods=("GET", "POST"))
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        error = None

        try:
            if not username:
                raise InputError("Username is required.")
            elif not password:
                raise InputError("Password is required.")
            elif len(password) < 6:
                raise InputError("Password must be at least 6 characters")
            db.session.add(User(username=username, password=generate_password_hash(password)))
            db.session.commit()
        except InputError as e:
            error = str(e)
        except IntegrityError:
            error = f"User {username} is already registered."
        else:
            return redirect(url_for("index"))

        flash(error)

    return render_template("auth/register.html")


@bp.route("/login", methods=("GET", "POST"))
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = db.session.scalars(select(User).where(User.username == username)).first()
        error = None

        try:
            if user is None:
                raise InputError("Incorrect username.")
            elif not check_password_hash(user.password, password):
                raise InputError("Incorrect password.")
        except InputError as e:
            error = str(e)
        else:
            session.clear()
            session["user_id"] = user.id
            return redirect(url_for("index"))

        flash(error)

    return render_template("auth/login.html")


@bp.before_app_request
def load_logged_in_user():
    user_id = session.get("user_id")

    if user_id is None:
        g.user = None
    else:
        g.user = db.session.scalars(select(User).where(User.id == user_id)).first()


@bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        return redirect(url_for("auth.login")) if g.user is None else view(**kwargs)

    return wrapped_view
