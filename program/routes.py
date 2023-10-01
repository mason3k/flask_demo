from program import app
from flask import render_template


@app.route("/")
@app.route("/index")
def index():
    return render_template("index.html")


@app.route("/100days")
def _100days():
    return render_template("100days.html")


@app.route("/syd")
def syd():
    return "Hello Syd"
