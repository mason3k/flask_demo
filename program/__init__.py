import contextlib
import os
from pathlib import Path

import click
from dotenv import load_dotenv
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from langid import langid
from sqlalchemy.orm import DeclarativeBase

load_dotenv()

MODEL = langid.LanguageIdentifier.from_modelstring(langid.model, norm_probs=True)


class Base(DeclarativeBase):
    ...


db = SQLAlchemy(model_class=Base)


def normalize_probability(prob):
    prob_exp = [0 if x == float("-inf") else math.exp(x) for x in prob]
    prob_exp_sum = sum(prob_exp)
    return prob_exp / prob_exp_sum

@click.command("init-db")
def init_db_command():
    """Clear the existing data and create new tables."""
    db.drop_all()
    db.create_all()
    click.echo("Initialized the database.")

def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.environ["SECRET_KEY"],
        SQLALCHEMY_DATABASE_URI=os.environ["DATABASE_URL"],
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile("config.py", silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    # ensure the instance folder exists
    with contextlib.suppress(OSError):
        Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    from . import auth, generator

    # register db
    db.init_app(app)

    # register cli commands
    app.cli.add_command(init_db_command)

    # register blueprints
    app.register_blueprint(auth.bp, url_prefix="/auth")
    app.register_blueprint(generator.bp)
    app.add_url_rule("/", endpoint="index", view_func=generator.index)

    # load langid model
    langid.load_model()

    with app.app_context():
        db.create_all()

    return app
