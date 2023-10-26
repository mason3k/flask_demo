import contextlib
import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask
from langid import langid

load_dotenv()

MODEL = langid.LanguageIdentifier.from_modelstring(langid.model, norm_probs=True)


def normalize_probability(prob):
    prob_exp = [0 if x == float("-inf") else math.exp(x) for x in prob]
    prob_exp_sum = sum(prob_exp)
    return prob_exp / prob_exp_sum


def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.environ["SECRET_KEY"],
        DATABASE=os.path.join(app.instance_path, "program.sqlite"),
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

    from . import auth, db, generator

    # register db
    db.init_app(app)

    # register blueprints
    app.register_blueprint(auth.bp, url_prefix="/auth")
    app.register_blueprint(generator.bp)
    app.add_url_rule("/", endpoint="index", view_func=generator.index)

    # load langid model
    langid.load_model()

    return app
