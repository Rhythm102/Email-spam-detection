from flask import Flask, render_template, request, jsonify
import pickle
from gmail_reader import fetch_latest_emails

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
    emails = fetch_latest_emails(limit=5)

    formatted = []
    for e in emails:
        formatted.append({
            "subject": e["subject"],
            "sender": e["from"],
            "body": e["body"]
        })

    return jsonify({"emails": formatted})

if __name__ == "__main__":
    app.run(debug=True)
