import contextlib
import os
from pathlib import Path

import click
from dotenv import load_dotenv
from flask import Flask
from flask_mail import Mail
from flask_security import Security, SQLAlchemyUserDatastore, hash_password
from langid import langid

from .db import db
from .models import Role, User

load_dotenv()

MODEL = langid.LanguageIdentifier.from_modelstring(langid.model, norm_probs=True)

user_datastore = SQLAlchemyUserDatastore(db, User, Role)
mail = Mail()

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
        SQLALCHEMY_DATABASE_URI="sqlite:///program.sqlite",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SECURITY_PASSWORD_SALT=os.environ.get(
            "SECURITY_PASSWORD_SALT", "146585145368132386173505678016728509634"
        ),
        REMEMBER_COOKIE_SAMITESITE="strict",
        SESSION_COOKIE_SAMITESITE="strict",
        SQLALCHEMY_ENGINE_OPTIONS={"pool_pre_ping": True},
        SECURITY_REGISTERABLE = True,
        MAIL_SERVER = 'smtp.gmail.com',
        MAIL_PORT = 465,
        # MAIL_USE_TLS = True,
        MAIL_USE_SSL = True,
        MAIL_USERNAME = os.environ['MAIL_USERNAME'],
        MAIL_PASSWORD = os.environ['MAIL_PASSWORD'],
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

    # initialize email
    mail.init_app(app)

    # setup security
    app.security = Security(app, user_datastore)

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
        if not app.security.datastore.find_user(email="test@me.com"):
            app.security.datastore.create_user(
                email="test@me.com", password=hash_password("password")
            )
        db.session.commit()

    return app

