from program import app


@app.route("/")
@app.route("/index")
def index():
    return "Hello Pythonistas"


@app.route("/syd")
def syd():
    return "Hello Syd"
