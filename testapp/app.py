"""
Intentionally vulnerable test app for exercising the access-control-agent.
Do not deploy. Auth is a toy bearer-token scheme, not production-grade.
"""
from flask import Flask, request, jsonify

app = Flask(__name__)

USERS = {
    "alice-token": {"id": 1, "username": "alice", "role": "user"},
    "bob-token": {"id": 2, "username": "bob", "role": "user"},
    "admin-token": {"id": 3, "username": "admin", "role": "admin"},
}

ORDERS = {
    101: {"id": 101, "owner_id": 1, "item": "Laptop", "total": 1200},
    102: {"id": 102, "owner_id": 2, "item": "Headphones", "total": 200},
}

PROFILES = {
    1: {"id": 1, "username": "alice", "email": "alice@example.com"},
    2: {"id": 2, "username": "bob", "email": "bob@example.com"},
}

COUPON_REDEEMED = {"WELCOME10": set()}  # username -> redeemed


def current_user():
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    return USERS.get(token)


@app.get("/api/orders/<int:order_id>")
def get_order(order_id):
    # VULNERABLE: IDOR — no check that order.owner_id == current user's id
    user = current_user()
    if not user:
        return jsonify({"error": "unauthorized"}), 401
    order = ORDERS.get(order_id)
    if not order:
        return jsonify({"error": "not found"}), 404
    return jsonify(order)


@app.get("/api/profile/<int:user_id>")
def get_profile(user_id):
    # NOT vulnerable: proper ownership + admin-override check (negative control)
    user = current_user()
    if not user:
        return jsonify({"error": "unauthorized"}), 401
    if user["id"] != user_id and user["role"] != "admin":
        return jsonify({"error": "forbidden"}), 403
    profile = PROFILES.get(user_id)
    if not profile:
        return jsonify({"error": "not found"}), 404
    return jsonify(profile)


@app.get("/admin/stats")
def admin_stats():
    # VULNERABLE: vertical privilege escalation — trusts a client-supplied
    # header instead of the authenticated user's server-side role.
    user = current_user()
    if not user:
        return jsonify({"error": "unauthorized"}), 401
    is_admin_header = request.headers.get("X-Admin") == "true"
    if not is_admin_header:
        return jsonify({"error": "forbidden"}), 403
    return jsonify({"total_orders": len(ORDERS), "total_users": len(USERS)})


@app.post("/api/coupon/redeem")
def redeem_coupon():
    # VULNERABLE: business logic bypass — no idempotency/one-time enforcement
    user = current_user()
    if not user:
        return jsonify({"error": "unauthorized"}), 401
    code = request.json.get("code") if request.is_json else None
    if code not in COUPON_REDEEMED:
        return jsonify({"error": "invalid code"}), 400
    COUPON_REDEEMED[code].add(user["username"])
    return jsonify({"status": "redeemed", "code": code, "discount": 10})


if __name__ == "__main__":
    app.run(port=5055)
