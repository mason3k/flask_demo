import os
from dataclasses import dataclass

import httpx
from flask import (
    Blueprint,
    flash,
    g,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_security import auth_required, current_user
from iso639 import Lang
from sqlalchemy import false, select
from werkzeug.exceptions import abort

from program.auth import login_required
from program.config import Config

# from program.db import get_db
from . import MODEL
from .db import db
from .models import Entry, User

KEY = os.environ["DETECTOR_API_KEY"]
bp = Blueprint("generator", __name__)


@dataclass(frozen=True)
class LangResult:
    language: str
    certainty: float


@bp.route("/index")
@auth_required()
def index():
    # db.session.add(User(email="test1@me.com", password="hi", active=True, fs_uniquifier=uuid.uuid4().hex))
    # raise Exception(db.session.query(User).filter_by(email="test@me.com").first())
    # raise Exception([user for user in db.session.execute(select(User)).scalars()])
    rpp = Config.ROWS_PER_PAGE
    page_num = request.args.get("page", 1, type=int)
    if g.user:
        s = select(Entry).where(Entry.author_id == g.user.id).order_by(Entry.created.desc())
    else:
        s = select(Entry).filter(false())
    page = db.paginate(s, page=page_num, per_page=rpp)
    return render_template(
        "generator/index.html",
        page=page,
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
            min((result["confidence"] / 10), 1),
        )
    return LangResult(Lang(language).name, certainty)


@bp.route("/create", methods=("GET", "POST"))
@login_required
def create():
    if request.method != "POST":
        return render_template("generator/create.html", default_mode=Config.DEFAULT_MODE)
    
    text = request.form["text"].strip()
    error = None if text else "Text is required."
    if error is not None:
        flash(error, category="error")
    else:
        offline = bool(request.form.get("offline-mode", 0))
        try:
            result = detect_language(text, offline_mode=offline)
        except Exception as e:
            flash(f"Problem detecting language: {e}", category="error")
        else:
            db.session.add(
                Entry(
                    text=text,
                    language=result.language,
                    certainty=result.certainty,
                    offline=offline,
                    author_id=g.user.id,
                )
            )
            db.session.commit()

            return render_template(
                "generator/result.html",
                text=text,
                language=result.language,
                certainty=result.certainty,
            )
        
    return render_template("generator/create.html", default_mode=Config.DEFAULT_MODE)


def get_entry(id, check_author=True):
    entry = db.one_or_404(db.select(Entry).filter_by(id=id), description=f"Entry id {id} doesn't exist.")

    if check_author and entry.author_id != g.user.id:
        abort(403)

    return entry


@bp.route("/<int:id>/update", methods=("GET", "POST"))
@login_required
def update(id):
    entry = get_entry(id)
    if request.method != "POST":
        return render_template("generator/update.html", entry=entry)

    text = request.form["text"].strip()
    error = None if text else "Text is required."
    if error is not None:
        flash(error, category="error")
    else:
        offline = bool(request.form.get("offline-mode", 0))
        try:
            result = detect_language(text, offline_mode=offline)
        except Exception as e:
            flash(f"Problem detecting language: {e}", category="error")
        else:
            entry = get_entry(id)
            entry.text=text
            entry.language = result.language
            entry.certainty = result.certainty
            entry.offline = offline
            db.session.commit()

            return render_template(
                "generator/result.html",
                text=text,
                language=result.language,
                certainty=result.certainty,
            )
        
    return render_template("generator/update.html", entry=entry)


@bp.route("/search", methods=("GET", "POST"))
@login_required
def search():
    search_t = request.form.get("search_url")
    if search_t == "":
        return render_template("index.html", error="Please enter a search term")
    entries = db.session.execute(
        select(Entry).where(Entry.text.like(f"%{search_t}%"), Entry.author_id == g.user.id)
    ).scalars()

    return render_template(
        "generator/search.html", entries=entries, search_tag=search_t
    )


@bp.route("/<int:id>/delete", methods=("POST",))
@login_required
def delete(id):
    entry = get_entry(id)
    db.session.delete(entry)
    db.session.commit()
    return redirect(url_for("generator.index"))

@bp.before_app_request
def load_logged_in_user():
    if not current_user.is_authenticated:
        g.user = None
    else:
        g.user = db.session.scalars(select(User).where(User.id == current_user.id)).first()
