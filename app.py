import os
import secrets
from dotenv import load_dotenv

load_dotenv()
from datetime import datetime, date, timedelta
from functools import wraps
from pathlib import Path

from flask import Flask, jsonify, render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash, generate_password_hash

from database import init_db, get_db, create_order, get_order, list_orders, update_order
from products import PRODUCTS

BASE_DIR = Path(__file__).resolve().parent
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "local-dev-change-this-secret-key")
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("COOKIE_SECURE", "0") == "1"

WHATSAPP_NUMBER = "".join(c for c in os.environ.get("WHATSAPP_NUMBER", "919876543210") if c.isdigit())
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD_HASH = os.environ.get("ADMIN_PASSWORD_HASH", "")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "ChangeThisPassword123!")

init_db()


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("admin_login", next=request.path))
        return fn(*args, **kwargs)
    return wrapper


@app.after_request
def security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


@app.get("/")
def home():
    return render_template("index.html")


@app.get("/api/products")
def api_products():
    return jsonify([
        {
            "id": p["id"], "name": p["name"], "description": p["description"],
            "category": p["category"], "variants": p["variants"], "image": p["image"],
            "price": p.get("price")
        } for p in PRODUCTS
    ])


@app.post("/api/orders")
def api_create_order():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    phone = "".join(c for c in (data.get("phone") or "") if c.isdigit())
    address = (data.get("address") or "").strip()
    notes = (data.get("notes") or "").strip()
    items = data.get("items") or []

    if not name or len(name) > 100:
        return jsonify(error="Please enter a valid name."), 400
    if len(phone) < 10 or len(phone) > 15:
        return jsonify(error="Please enter a valid phone number with country code if applicable."), 400
    if len(address) < 8 or len(address) > 1000:
        return jsonify(error="Please enter a complete delivery address."), 400
    if not isinstance(items, list) or not items or len(items) > 30:
        return jsonify(error="Your cart is empty or contains too many items."), 400

    catalog = {p["id"]: p for p in PRODUCTS}
    clean_items = []
    total = 0.0
    has_unpriced = False

    for item in items:
        pid = str(item.get("product_id", ""))
        variant = str(item.get("variant", "")).strip()
        try:
            qty = int(item.get("quantity", 0))
        except (TypeError, ValueError):
            qty = 0
        product = catalog.get(pid)
        if not product or qty < 1 or qty > 50:
            return jsonify(error="One of the cart items is invalid. Please refresh and try again."), 400
        allowed_variants = [v["name"] for v in product["variants"]]
        selected_variant = next((v for v in product["variants"] if v["name"] == variant), None)
        if not selected_variant:
            return jsonify(error=f"Invalid pack/variant for {product['name']}."), 400
        unit_price = selected_variant.get("price")
        if unit_price is None:
            has_unpriced = True
        else:
            total += float(unit_price) * qty
        clean_items.append({
            "product_id": pid, "product_name": product["name"],
            "variant": variant, "quantity": qty,
            "unit_price": unit_price
        })

    order_id = create_order(
        name=name, phone=phone, address=address, notes=notes,
        items=clean_items, total=round(total, 2) if not has_unpriced else None
    )
    order = get_order(order_id)
    lines = [
        "Vanakkam Renukambal Home Foods!",
        f"I would like to place order {order['order_number']}.",
        "",
        f"Name: {name}",
        f"Phone: {phone}",
        f"Delivery address: {address}",
        "",
        "Order items:"
    ]
    for item in clean_items:
        price_text = f" - Rs.{item['unit_price']:.2f} each" if item["unit_price"] is not None else " - price to be confirmed"
        lines.append(f"- {item['product_name']} ({item['variant']}) x {item['quantity']}{price_text}")
    lines.extend(["", f"Order total: Rs.{total:.2f}" if not has_unpriced else "Order total: To be confirmed"])
    if notes:
        lines.extend(["", f"Additional notes: {notes}"])
    lines.extend(["", "Please confirm availability and tentative delivery date."])
    whatsapp_url = f"https://wa.me/{WHATSAPP_NUMBER}?text={__import__('urllib.parse').parse.quote(chr(10).join(lines))}"
    return jsonify(order_id=order_id, order_number=order["order_number"], whatsapp_url=whatsapp_url)


@app.get("/order-success/<int:order_id>")
def order_success(order_id):
    order = get_order(order_id)
    if not order:
        return "Order not found", 404
    return render_template("order_success.html", order=order)


@app.get("/admin/login")
def admin_login():
    return render_template("admin_login.html")


@app.post("/admin/login")
def admin_login_post():
    username = request.form.get("username", "")
    password = request.form.get("password", "")
    stored_hash = ADMIN_PASSWORD_HASH or generate_password_hash(ADMIN_PASSWORD)
    if username == ADMIN_USERNAME and check_password_hash(stored_hash, password):
        session.clear()
        session["admin_logged_in"] = True
        session["csrf_token"] = secrets.token_urlsafe(32)
        return redirect(request.args.get("next") or url_for("admin_dashboard"))
    flash("Invalid username or password.", "error")
    return redirect(url_for("admin_login"))


@app.post("/admin/logout")
@admin_required
def admin_logout():
    session.clear()
    return redirect(url_for("admin_login"))


@app.get("/admin")
@admin_required
def admin_dashboard():
    status = request.args.get("status", "")
    search = request.args.get("q", "")
    orders = list_orders(status=status, search=search)
    return render_template("admin_dashboard.html", orders=orders, selected_status=status, search=search)


@app.get("/admin/orders/<int:order_id>")
@admin_required
def admin_order_detail(order_id):
    order = get_order(order_id)
    if not order:
        return "Order not found", 404
    return render_template("admin_order_detail.html", order=order, csrf_token=session.get("csrf_token"))


@app.post("/admin/orders/<int:order_id>/update")
@admin_required
def admin_order_update(order_id):
    if request.form.get("csrf_token") != session.get("csrf_token"):
        return "Invalid request token", 400
    status = request.form.get("status", "")
    delivery_date = request.form.get("delivery_date", "").strip() or None
    remarks = request.form.get("remarks", "").strip()
    valid_statuses = {"New", "Confirmed", "Preparing", "Ready", "Dispatched", "Delivered", "Cancelled"}
    if status not in valid_statuses:
        flash("Invalid order status.", "error")
        return redirect(url_for("admin_order_detail", order_id=order_id))
    update_order(order_id, status=status, delivery_date=delivery_date, remarks=remarks)
    flash("Order updated.", "success")
    return redirect(url_for("admin_order_detail", order_id=order_id))


@app.get("/health")
def health():
    return jsonify(status="ok", app="Renukambal Home Foods")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "5000")), debug=os.environ.get("FLASK_DEBUG", "1") == "1")
