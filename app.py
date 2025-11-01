from flask import Flask, request, jsonify, url_for
from flask_cors import CORS
from flask_mail import Mail, Message
from pymongo import MongoClient
import jwt
import datetime
import os

# ------------------------------
# CONFIGURATION
# ------------------------------
app = Flask(__name__)
CORS(app)

# --- Secret and Email Config ---
app.config["SECRET_KEY"] = "rebellion"  # change this in production
app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USERNAME"] = "strixus17@gmail.com"
app.config["MAIL_PASSWORD"] = "mqik dctt ixkq gwwl"

mail = Mail(app)

# --- MongoDB Setup ---
MONGO_URI = "mongodb+srv://yazidmoundher_db_user:L9chQ2YsVoEITXIl@cluster0.siqi7ho.mongodb.net/?appName=Cluster0"  # or your Mongo Atlas URI
client = MongoClient(MONGO_URI)
db = client["questup"]
devup_emails = db["devup_emails"]     # pre-existing users
event_emails = db["event_emails"]     # new event registrations

# --- Limits ---
MAX_GLOBAL_PARTICIPANTS = 80
DEPARTMENT_LIMITS = {
    "marketing": 10,
    "visual": 20,
    "event": 10,
    "design": 20,
    "developement": 20
}


# ------------------------------
# HELPER FUNCTIONS
# ------------------------------
def generate_verification_token(email):
    payload = {
        "email": email,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    }
    return jwt.encode(payload, app.config["SECRET_KEY"], algorithm="HS256")


def verify_token(token):
    try:
        payload = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
        return payload["email"]
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def send_verification_email(email, token):
    verify_url = url_for("verify_email_token", token=token, _external=True)
    msg = Message(
        subject="Verify Your Email",
        sender=app.config["MAIL_USERNAME"],
        recipients=[email],
        body=f"Welcome! Please verify your email by clicking this link:\n\n{verify_url}\n\nThis link expires in 1 hour."
    )
    mail.send(msg)


def count_total_participants():
    return event_emails.count_documents({})


def can_join_departments(departments):
    if count_total_participants() >= MAX_GLOBAL_PARTICIPANTS:
        return False, "Global participant limit reached (max 80)."

    for dept in departments:
        if dept not in DEPARTMENT_LIMITS:
            return False, f"Invalid department: {dept}"

        count = event_emails.count_documents({"departments": dept})
        if count >= DEPARTMENT_LIMITS[dept]:
            return False, f"Department '{dept}' is full."

    return True, "OK"


# ------------------------------
# ROUTES
# ------------------------------

@app.route("/register", methods=["POST"])
def register_participant():
    """
    Registers a new participant into event_emails collection.
    Sends a verification link via email.
    """
    data = request.get_json()
    name = data.get("name")
    email = data.get("email")
    departments = data.get("departments", [])

    if not name or not email or not departments:
        return jsonify({"error": "Missing required fields"}), 400

    # Check if already registered in event_emails
    if event_emails.find_one({"email": email.lower()}):
        return jsonify({"error": "Email already registered"}), 400

    ok, msg = can_join_departments(departments)
    if not ok:
        return jsonify({"error": msg}), 400

    # Create record in event_emails
    new_participant = {
        "name": name,
        "email": email.lower(),
        "departments": departments,
        "verified": False,
        "created_at": datetime.datetime.utcnow()
    }

    event_emails.insert_one(new_participant)

    # Send verification link
    token = generate_verification_token(email)
    send_verification_email(email, token)

    return jsonify({
        "message": "Registration successful. Verification email sent.",
        "participant": {
            "name": name,
            "email": email,
            "departments": departments,
            "verified": False
        }
    }), 201


@app.route("/verify/<token>", methods=["GET"])
def verify_email_token(token):
    """
    When the user clicks the verification link, update their 'verified' status in event_emails.
    """
    email = verify_token(token)
    if not email:
        return jsonify({"error": "Invalid or expired token"}), 400

    user = event_emails.find_one({"email": email.lower()})
    if not user:
        return jsonify({"error": "Email not found"}), 404

    event_emails.update_one({"email": email.lower()}, {"$set": {"verified": True}})
    return jsonify({"message": "Email verified successfully", "email": email}), 200


@app.route("/verify_email/<email>", methods=["GET"])
def verify_email(email):
    """
    Checks if email exists in the devup_emails collection (not event_emails).
    """
    exists = bool(devup_emails.find_one({"email": email.lower()}))
    return jsonify({"email": email, "registered": exists}), 200


@app.route("/verify_limits", methods=["GET"])
def verify_limits():
    """
    Checks department and global capacity using event_emails collection.
    """
    total = count_total_participants()
    global_full = total >= MAX_GLOBAL_PARTICIPANTS
    department_status = {}
    for dept in DEPARTMENT_LIMITS:
        count = event_emails.count_documents({"departments": dept})
        department_status[dept] = {
            "count": count,
            "limit": DEPARTMENT_LIMITS[dept],
            "full": count >= DEPARTMENT_LIMITS[dept]
        }

    return jsonify({
        "total_participants": total,
        "global_limit": MAX_GLOBAL_PARTICIPANTS,
        "global_full": global_full,
        "departments": department_status
    }), 200


# ------------------------------
# ENTRY POINT
# ------------------------------
if __name__ == "__main__":
    app.run(debug=True)
