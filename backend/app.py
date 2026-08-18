import requests

from flask import Flask, jsonify, request

from config import PORT, WARM_AE, allowed_origins
from ae_catalog import maintain_loop
from prices import card_price

app = Flask(__name__)


@app.after_request
def cors(response):
    origin = (request.headers.get("Origin") or "").rstrip("/")
    allowed = {item.rstrip("/") for item in allowed_origins}
    if "*" in allowed:
        allow = "*"
    elif origin in allowed:
        allow = origin
    else:
        allow = "null"
    response.headers["Access-Control-Allow-Origin"] = allow
    response.headers["Vary"] = "Origin"
    return response


@app.get("/health")
def health():
    return jsonify(ok=True)


@app.get("/api/card-price")
def api_card_price():
    name = request.args.get("name", "").strip()
    selected_title = request.args.get("title", "").strip() or None
    try:
        page = max(0, int(request.args.get("page", 0)))
    except ValueError:
        return jsonify(error="Invalid candidate offset"), 400
    candidates_only = request.args.get("candidates_only") == "1"
    include_ae = request.args.get("include_ae") == "1"
    if len(name) < 3:
        return jsonify(error="Enter at least 3 characters"), 400
    if len(name) > 100:
        return jsonify(error="Card name must be 100 characters or fewer"), 400
    try:
        return jsonify(card_price(name, selected_title, page, candidates_only, include_ae))
    except (requests.RequestException, ValueError) as error:
        return jsonify(error=str(error)), 502


if WARM_AE:
    import threading
    threading.Thread(target=maintain_loop, daemon=True).start()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
