from urllib.parse import parse_qs, urlparse
from flask import Flask, current_app, request

from main import TitleType, summarize

app = Flask(__name__)


@app.route("/summarize")
def get_summary():
    url = urlparse(request.args.get("url"))
    queries = parse_qs(url.query)
    if "v" not in queries:
        return "Invalid url", 400
    id = parse_qs(url.query)["v"][0]
    if id:
        print(id)
        return summarize(id, TitleType.GENERAL)["summary"]
    else:
        return "Invalid url", 400


@app.route("/")
def index():
    return current_app.send_static_file("index.html")
