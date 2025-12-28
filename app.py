from flask import Flask, render_template, request, jsonify, redirect, session
import pickle
import os
from werkzeug.middleware.proxy_fix import ProxyFix
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1' if os.environ.get('DEBUG') == 'True' else '0'
os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'

# -------------------- CONFIG --------------------

app = Flask(__name__)
#TELL FLASK TO TRUST RENDER'S PROXY
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
#ESSENTIAL SESSION SETTINGS FOR RENDER
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "any-random-long-string")
app.config.update(
    SESSION_COOKIE_SECURE=True,   # Send cookies over HTTPS only
    SESSION_COOKIE_SAMESITE='Lax', # Required for OAuth redirects
)

# 3. TELL GOOGLE TO ALLOW REDIRECTS
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

# -------------------- LOAD ML MODEL --------------------

model = pickle.load(open("spam_model.pkl", "rb"))
vectorizer = pickle.load(open("vectorizer.pkl", "rb"))

# -------------------- HOME --------------------

@app.route("/")
def home():
    return render_template("index.html")

# -------------------- SPAM PREDICTION --------------------

@app.route("/predict", methods=["POST"])
def predict():
    data = request.get_json()
    content = data.get("content", "").strip()

    if not content:
        return jsonify({"error": "Empty content"}), 400

    transformed = vectorizer.transform([content])
    prediction = model.predict(transformed)[0]

    return jsonify({"spam": bool(prediction)})

# -------------------- GOOGLE LOGIN --------------------

@app.route("/login")
def login():
    # Use the variable from Render environment
    redirect_uri = os.environ.get("GOOGLE_REDIRECT_URI")
    
    flow = Flow.from_client_config(
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
    )

    flow.redirect_uri = redirect_uri
    auth_url, _ = flow.authorization_url(access_type="offline", prompt="consent")
    return redirect(auth_url)

# -------------------- OAUTH CALLBACK --------------------

@app.route("/oauth2callback")
def oauth2callback():
    redirect_uri = os.environ.get("GOOGLE_REDIRECT_URI")
    
    flow = Flow.from_client_config(
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
    )

    flow.redirect_uri = redirect_uri
    
    # FIX: Force the response URL to be HTTPS so it matches your Google Console
    authorization_response = request.url.replace("http://", "https://")
    
    flow.fetch_token(authorization_response=authorization_response)

    credentials = flow.credentials
    # SAVE TO SESSION
    session["credentials"] = {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": credentials.scopes,
    }
    
    # Force session to save
    session.modified = True 

    return redirect("/")

# -------------------- GMAIL SERVICE --------------------

def get_gmail_service():
    if "credentials" not in session:
        return None

    creds = Credentials(**session["credentials"])

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        session["credentials"]["token"] = creds.token

    return build("gmail", "v1", credentials=creds)

# -------------------- FETCH GMAIL --------------------

@app.route("/fetch-gmail")
def fetch_gmail():
    service = get_gmail_service()

    if not service:
        return jsonify({
            "error": "Not authenticated",
            "login_url": "/login"
        }), 401

    results = service.users().messages().list(
        userId="me",
        maxResults=5
    ).execute()

    messages = results.get("messages", [])
    emails = []

    for msg in messages:
        msg_data = service.users().messages().get(
            userId="me",
            id=msg["id"],
            format="full"
        ).execute()

        headers = msg_data["payload"]["headers"]
        subject = sender = ""

        for h in headers:
            if h["name"] == "Subject":
                subject = h["value"]
            if h["name"] == "From":
                sender = h["value"]

        body = ""
        parts = msg_data["payload"].get("parts", [])
        for part in parts:
            if part["mimeType"] == "text/plain":
                body = part["body"].get("data", "")
                break

        emails.append({
            "subject": subject,
            "sender": sender,
            "body": body
        })

    return jsonify({"emails": emails})

# -------------------- RUN LOCAL --------------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)






