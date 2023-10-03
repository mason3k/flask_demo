from flask import Blueprint, flash, g, redirect, render_template, request, url_for
from werkzeug.exceptions import abort

from program.auth import login_required
from program.db import get_db
from langid.langid import classify
from . import MODEL
from iso639 import Lang

bp = Blueprint("generator", __name__)


@bp.route("/")
def index():
    db = get_db()
    entries = db.execute(
        "SELECT p.id, text, language, certainty, created, author_id, username"
        " FROM entry p JOIN user u ON p.author_id = u.id"
        " ORDER BY created DESC"
    ).fetchall()
    return render_template("generator/index.html", entries=entries)


@bp.route("/create", methods=("GET", "POST"))
@login_required
def create():
    if request.method == "POST":
        text = request.form["text"]
        error = None if text else "Text is required."
        if error is not None:
            flash(error)
        else:
            db = get_db()
            language, certainty = MODEL.classify(text)
            language = Lang(language).name
            db.execute(
                "INSERT INTO entry (text, language, certainty, author_id)" " VALUES (?, ?, ?, ?)",
                (text, language, certainty, g.user["id"]),
            )
            db.commit()
            return redirect(url_for("generator.index"))

    return render_template("generator/create.html")


def get_entry(id, check_author=True):
    entry = (
        get_db()
        .execute(
            "SELECT p.id, text, language, certainty, created, author_id, username"
            " FROM entry p JOIN user u ON p.author_id = u.id"
            " WHERE p.id = ?",
            (id,),
        )
        .fetchone()
    )

    if entry is None:
        abort(404, f"Entry id {id} doesn't exist.")

    if check_author and entry["author_id"] != g.user["id"]:
        abort(403)

    return entry


@bp.route("/<int:id>/update", methods=("GET", "POST"))
@login_required
def update(id):
    entry = get_entry(id)
    if request.method != "POST":
        return render_template("generator/update.html", entry=entry)

    text = request.form["text"]
    error = None if text else "Text is required."
    if error is not None:
        flash(error)
    else:
        db = get_db()
        text = request.form["text"]
        language, certainty = MODEL.classify(text)
        language = Lang(language).name
        db.execute(
            "UPDATE entry SET text = ?, language = ?, certainty = ?" " WHERE id = ?", (text, language, certainty, id)
        )
        db.commit()
        return redirect(url_for("generator.index"))


@bp.route("/search", methods=("GET", "POST"))
@login_required
def search():
    search_t = request.form.get("search_url")
    if search_t == "":
        return render_template("index.html", error="Please enter a search term")
    db = get_db()
    entries = db.execute(
        "SELECT p.id, text, language, certainty, created, author_id, username"
        " FROM entry p JOIN user u ON p.author_id = u.id"
        " WHERE text like ?"
        " ORDER BY created DESC",
        (f"%{search_t}%",),
    ).fetchall()

    return render_template("generator/search.html", entries=entries, search_tag=search_t)


@bp.route("/<int:id>/delete", methods=("POST",))
@login_required
def delete(id):
    get_entry(id)
    db = get_db()
    db.execute("DELETE FROM entry WHERE id = ?", (id,))
    db.commit()
    return redirect(url_for("generator.index"))
