from flask import Flask, render_template, request, jsonify
import pickle
from gmail_reader import fetch_latest_emails
import os
from googleapiclient.discovery import build
from flask import redirect, request, jsonify
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
import json
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
@app.route("/login")
def login():
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": os.environ["GOOGLE_CLIENT_ID"],
                "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [os.environ["GOOGLE_REDIRECT_URI"]],
            }
        },
        scopes=SCOPES,
    )

    flow.redirect_uri = os.environ["GOOGLE_REDIRECT_URI"]

    auth_url, _ = flow.authorization_url(
        access_type="offline",
        prompt="consent"
    )

    return redirect(auth_url)
@app.route("/oauth2callback")
def oauth2callback():
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": os.environ["GOOGLE_CLIENT_ID"],
                "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [os.environ["GOOGLE_REDIRECT_URI"]],
            }
        },
        scopes=SCOPES,
    )

    flow.redirect_uri = os.environ["GOOGLE_REDIRECT_URI"]

    flow.fetch_token(authorization_response=request.url)
    creds = flow.credentials

    with open("token.json", "w") as token:
        token.write(creds.to_json())

    return "✅ Gmail connected successfully! You can close this tab."
def get_gmail_service():
    if not os.path.exists("token.json"):
        return None

    creds = Credentials.from_authorized_user_file(
        "token.json",
        SCOPES
    )

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)    


app = Flask(__name__)

# Load ML model
model = pickle.load(open("spam_model.pkl", "rb"))
vectorizer = pickle.load(open("vectorizer.pkl", "rb"))

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/predict", methods=["POST"])
def predict():
    data = request.get_json()
    content = data.get("content", "")

    if not content.strip():
        return jsonify({"error": "Empty content"}), 400

    transformed = vectorizer.transform([content])
    prediction = model.predict(transformed)[0]

    return jsonify({
        "spam": bool(prediction)
    })

@app.route("/fetch-gmail", methods=["GET"])
def fetch_gmail():
    service = get_gmail_service()

    if not service:
        return jsonify({
            "error": "Not authenticated",
            "login_url": "/login"
        }), 401

if __name__ == "__main__":
    app.run(debug=True)


