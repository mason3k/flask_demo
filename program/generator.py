import os
from dataclasses import dataclass

import httpx
from flask import Blueprint, flash, g, redirect, render_template, request, url_for
from iso639 import Lang
from werkzeug.exceptions import abort

from program.auth import login_required
from program.config import Config
from program.db import get_db

from . import MODEL

KEY = os.environ["DETECTOR_API_KEY"]
bp = Blueprint("generator", __name__)


@dataclass(frozen=True)
class LangResult:
    language: str
    certainty: float


@bp.route("/index")
def index():
    rpp = Config.ROWS_PER_PAGE
    page = request.args.get("page", 1, type=int)
    db = get_db()
    entries = db.execute(
        "SELECT p.id, text, language, certainty, created, author_id, username,"
        " COUNT() OVER() AS total_entries"
        " FROM entry p JOIN user u ON p.author_id = u.id"
        " ORDER BY created DESC"
        f" LIMIT {rpp} OFFSET {(page - 1)  * rpp}"
    ).fetchall()
    max_page = entries[0]["total_entries"] // rpp if entries else 0
    return render_template(
        "generator/index.html",
        entries=entries,
        active_page=page,
        max_page=max_page,
    )


def detect_language(text: str, offline_mode: bool = False) -> LangResult:
    if offline_mode:
        language, certainty = MODEL.classify(text)
    else:
        r = httpx.post(
            "https://ws.detectlanguage.com/0.2/detect",
            headers={"Authorization": f"Bearer {KEY}"},
            json={"q": text},
        )
        r.raise_for_status()
        result = r.json()["data"]["detections"][0]
        language, certainty = (
            result["language"],
            min((result["confidence"] / 10), 100),
        )
    return LangResult(Lang(language).name, certainty)


@bp.route("/create", methods=("GET", "POST"))
@login_required
def create():
    if request.method == "POST":
        text = request.form["text"]
        offline = request.form.get("offline-mode", 0)
        error = None if text else "Text is required."
        if error is not None:
            flash(error)
        else:
            db = get_db()
            try:
                result = detect_language(text, offline_mode=bool(offline))
            except Exception as e:
                flash(f"Problem detecting language: {e}")
            else:
                db.execute(
                    "INSERT INTO entry (text, language, certainty, offline, author_id)"
                    " VALUES (?, ?, ?, ?, ?)",
                    (text, result.language, result.certainty, "1", g.user["id"]),
                )
                db.commit()
                return render_template(
                    "generator/result.html",
                    text=text,
                    language=result.language,
                    certainty=result.certainty,
                )

    return render_template("generator/create.html", default_mode=Config.DEFAULT_MODE)


def get_entry(id, check_author=True):
    entry = (
        get_db()
        .execute(
            "SELECT p.id, text, language, certainty, created, offline, author_id, username"
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
    offline = request.form.get("offline-mode", 0)
    error = None if text else "Text is required."
    if error is not None:
        flash(error)
    else:
        db = get_db()
        try:
            result = detect_language(text, offline_mode=bool(offline))
        except Exception as e:
            flash(f"Problem detecting language: {e}")
        else:
            db.execute(
                "UPDATE entry SET text = ?, language = ?, certainty = ?, offline = ?"
                " WHERE id = ?",
                (text, result.language, result.certainty, offline, id),
            )
            db.commit()
            return render_template(
                "generator/result.html",
                text=text,
                language=result.language,
                certainty=result.certainty,
            )


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

    return render_template(
        "generator/search.html", entries=entries, search_tag=search_t
    )


@bp.route("/<int:id>/delete", methods=("POST",))
@login_required
def delete(id):
    get_entry(id)
    db = get_db()
    db.execute("DELETE FROM entry WHERE id = ?", (id,))
    db.commit()
    return redirect(url_for("generator.index"))
