import os
import pickle
import base64
from flask import Flask, render_template, request, jsonify, redirect, session
from werkzeug.middleware.proxy_fix import ProxyFix
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# -------------------- CONFIG --------------------

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "any-random-long-string")

app.config.update(
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='None',
)

# Crucial for OAuth on Render
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

# -------------------- LOAD ML MODEL --------------------
# Using try-except to prevent crash if files are missing
try:
    model = pickle.load(open("spam_model.pkl", "rb"))
    vectorizer = pickle.load(open("vectorizer.pkl", "rb"))
except FileNotFoundError:
    print("Warning: Model files not found!")

# -------------------- HELPER: DECODE GMAIL BODY --------------------

def decode_gmail_body(payload):
    """Recursively find and decode the text/plain part of the email."""
    body = ""
    if 'parts' in payload:
        for part in payload['parts']:
            if part['mimeType'] == 'text/plain' and 'data' in part['body']:
                data = part['body']['data']
                body += base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
            elif 'parts' in part:
                body += decode_gmail_body(part)
    else:
        if 'data' in payload.get('body', {}):
            data = payload['body']['data']
            body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
    return body.strip()

# -------------------- GOOGLE AUTH ROUTES --------------------

def get_flow():
    redirect_uri = os.environ.get("GOOGLE_REDIRECT_URI")
    return Flow.from_client_config(
        {
            "web": {
                "client_id": os.environ["GOOGLE_CLIENT_ID"],
                "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [redirect_uri],
            }
        },
        scopes=SCOPES,
        redirect_uri=redirect_uri
    )

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/login")
def login():
    flow = get_flow()
    auth_url, _ = flow.authorization_url(access_type="offline", prompt="consent")
    return redirect(auth_url)

@app.route("/oauth2callback")
def oauth2callback():
    flow = get_flow()
    # Force HTTPS for the comparison
    authorization_response = request.url.replace("http://", "https://")
    flow.fetch_token(authorization_response=authorization_response)

    credentials = flow.credentials
    session["credentials"] = {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": credentials.scopes,
    }
    session.modified = True
    return redirect("/")

# -------------------- FETCH & PREDICT --------------------

@app.route("/fetch-gmail")
def fetch_gmail():
    if "credentials" not in session:
        return jsonify({"error": "Not authenticated", "login_url": "/login"}), 401

    creds = Credentials(**session["credentials"])
    
    # Refresh token if expired
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        session["credentials"]["token"] = creds.token
        session.modified = True

    service = build("gmail", "v1", credentials=creds)
    
    try:
        results = service.users().messages().list(userId="me", maxResults=5).execute()
        messages = results.get("messages", [])
        emails = []

        for msg in messages:
            msg_data = service.users().messages().get(userId="me", id=msg["id"], format="full").execute()
            
            headers = msg_data["payload"]["headers"]
            subject = next((h["value"] for h in headers if h["name"] == "Subject"), "No Subject")
            sender = next((h["value"] for h in headers if h["name"] == "From"), "Unknown")

            # Properly decode the body
            body = decode_gmail_body(msg_data["payload"])
            
            # Predict spam
            is_spam = False
            if body:
                transformed = vectorizer.transform([body])
                is_spam = bool(model.predict(transformed)[0])

            emails.append({
                "subject": subject,
                "sender": sender,
                "body": body[:200] + "...", # Truncate for display
                "is_spam": is_spam
            })

        return jsonify({"emails": emails})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    # FIX: Use the port provided by Render
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)








