from flask import Flask, send_from_directory, render_template, request, jsonify
import requests
import os

app = Flask(__name__, static_folder="static", template_folder="templates")

# FastAPI backend URL
FASTAPI_URL = "http://localhost:8000"  # Change this if FastAPI is hosted elsewhere

@app.route("/")
def serve_index():
    return send_from_directory(app.template_folder, "index.html")

@app.route("/<path:path>")
def static_proxy(path):
    return send_from_directory(app.static_folder, path)

@app.route("/chat", methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
def chat_proxy():
    user_query = request.json.get("query")
    try:
        response = requests.post(
            f"{FASTAPI_URL}/chat",
            json={"query": user_query},
            headers={"Content-Type": "application/json"},
        )
        return jsonify(response.json()), response.status_code
    except requests.exceptions.RequestException as e:
        return jsonify({"error": "Failed to reach backend", "details": str(e)}), 500

@app.route("/ingest", methods=["POST"])
def ingest_proxy():
    try:
        response = requests.post(f"{FASTAPI_URL}/ingest")
        return jsonify(response.json()), response.status_code
    except requests.exceptions.RequestException as e:
        return jsonify({"error": "Failed to reach backend", "details": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True,host='0.0.0.0', port=5000)
