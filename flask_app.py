from flask import Flask, request, jsonify
from flask_cors import CORS
app = Flask(__name__)
CORS(app)
# ------------------------------
# CONFIGURATION
# ------------------------------
MAX_GLOBAL_PARTICIPANTS = 80
DEPARTMENT_LIMITS = {
    "marketing": 10,
    "visual": 20,
    "event": 10,
    "design": 20,
    "developement": 20
}

# ------------------------------
# DATA STORAGE
# ------------------------------
participants = []  # List of dicts: {"name": str, "email": str, "departments": [str]}
department_counts = {dept: 0 for dept in DEPARTMENT_LIMITS}


# ------------------------------
# HELPER FUNCTIONS
# ------------------------------
def count_total_participants():
    return len(participants)


def can_join_departments(departments):
    """
    Check if new participant can join given departments without violating limits.
    """
    # Check global limit
    if count_total_participants() >= MAX_GLOBAL_PARTICIPANTS:
        return False, "Global participant limit reached (max 80)."

    # Check per-department limit
    for dept in departments:
        if dept not in DEPARTMENT_LIMITS:
            return False, f"Invalid department: {dept}"
        if department_counts[dept] >= DEPARTMENT_LIMITS[dept]:
            return False, f"Department '{dept}' is full."

    return True, "OK"


# ------------------------------
# ROUTES
# ------------------------------

@app.route("/register", methods=["POST"])
def register_participant():
    """
    Register a new participant.
    JSON input: {"name": str, "email": str, "departments": [str]}
    """
    data = request.get_json()

    name = data.get("name")
    email = data.get("email")
    departments = data.get("departments", [])

    # Basic validation
    if not name or not email or not departments:
        return jsonify({"error": "Missing required fields"}), 400

    # Check if email already registered
    if any(p["email"].lower() == email.lower() for p in participants):
        return jsonify({"error": "Email already registered"}), 400

    # Check limits
    ok, msg = can_join_departments(departments)
    if not ok:
        return jsonify({"error": msg}), 400

    # Register participant
    participants.append({"name": name, "email": email, "departments": departments})

    # Update department counts
    for dept in departments:
        department_counts[dept] += 1

    return jsonify({
        "message": "Registration successful",
        "participant": {"name": name, "email": email, "departments": departments}
    }), 201



@app.route("/verify_email/<email>", methods=["GET"])
def verify_email(email):
    """
    Check if an email is already registered.
    """
    exists = any(p["email"].lower() == email.lower() for p in participants)
    return jsonify({"email": email, "registered": exists}), 200


@app.route("/verify_limits", methods=["GET"])
def verify_limits():
    """
    Check if the global or department limits are reached.
    """
    total = count_total_participants()
    global_full = total >= MAX_GLOBAL_PARTICIPANTS
    department_status = {
        dept: {
            "count": count,
            "limit": DEPARTMENT_LIMITS[dept],
            "full": count >= DEPARTMENT_LIMITS[dept]
        }
        for dept, count in department_counts.items()
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
    app.run()
