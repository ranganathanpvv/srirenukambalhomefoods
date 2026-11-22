import os
import secrets
from urllib.parse import quote
from dotenv import load_dotenv

load_dotenv()
from functools import wraps
from pathlib import Path

from flask import Flask, jsonify, render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash, generate_password_hash

from database import init_db, create_order, get_order, list_orders, update_order, delete_order
from products import PRODUCTS, ORDER_CLAUSES

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

VALID_ORDER_STATUSES = {"New", "Confirmed", "Preparing", "Ready", "Dispatched", "Delivered", "Cancelled"}

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
    return render_template("index.html", order_clauses=ORDER_CLAUSES)


@app.get("/cart")
def cart_summary():
    return render_template("cart_summary.html", order_clauses=ORDER_CLAUSES)


@app.get("/api/products")
def api_products():
    return jsonify([
        {
            "id": p["id"],
            "name": p["name"],
            "description": p["description"],
            "category": p["category"],
            "variants": p["variants"],
            "attributes": p.get("attributes", []),
            "min_qty": p.get("min_qty", 1),
            "image": p["image"],
            "price": p.get("price"),
        }
        for p in PRODUCTS
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
        raw_attrs = item.get("attributes") or {}
        if not isinstance(raw_attrs, dict):
            return jsonify(error="Invalid product attributes."), 400

        product = catalog.get(pid)
        min_qty = int(product.get("min_qty", 1)) if product else 1
        try:
            qty = int(item.get("quantity", 0))
        except (TypeError, ValueError):
            qty = 0

        if not product or qty < min_qty or qty > 50:
            return jsonify(
                error=f"Quantity for {product['name'] if product else 'item'} must be at least {min_qty}."
            ), 400

        selected_variant = next((v for v in product["variants"] if v["name"] == variant), None)
        if not selected_variant:
            return jsonify(error=f"Invalid pack/variant for {product['name']}."), 400

        attr_delta_total = 0.0
        attr_has_unpriced = False
        chosen_attr_labels = []

        for attr_def in product.get("attributes", []):
            key = attr_def["key"]
            chosen_val = str(raw_attrs.get(key, "")).strip()
            matched_opt = next((o for o in attr_def["options"] if o["value"] == chosen_val), None)
            if not matched_opt:
                return jsonify(error=f"Please select a valid {attr_def['label']} for {product['name']}."), 400
            chosen_attr_labels.append(chosen_val)
            delta = matched_opt.get("price_delta", 0.0)
            if delta is None:
                attr_has_unpriced = True
            else:
                attr_delta_total += float(delta)

        pack_500 = next((v for v in product["variants"] if v["name"] == "500g"), None)
        if variant == "250g" and qty == 2 and pack_500 and pack_500.get("price") is not None:
            base_amount = float(pack_500["price"])
            applied_500_bundle = True
        else:
            base_unit_price = selected_variant.get("price")
            base_amount = float(base_unit_price) if base_unit_price is not None else None
            applied_500_bundle = False

        if base_amount is None or attr_has_unpriced:
            unit_price = None
            line_total = None
            has_unpriced = True
        elif applied_500_bundle:
            line_total = round(base_amount + attr_delta_total, 2)
            unit_price = round(line_total / 2, 2)
            total += line_total
        else:
            unit_price = round(base_amount + attr_delta_total, 2)
            line_total = round(unit_price * qty, 2)
            total += line_total

        variant_display = f"{variant} ({', '.join(chosen_attr_labels)})" if chosen_attr_labels else variant
        if applied_500_bundle:
            variant_display = f"{variant_display} [500g pack rate]"

        clean_items.append({
            "product_id": pid,
            "product_name": product["name"],
            "variant": variant_display,
            "quantity": qty,
            "unit_price": unit_price,
        })

    order_id = create_order(
        name=name,
        phone=phone,
        address=address,
        notes=notes,
        items=clean_items,
        total=round(total, 2) if not has_unpriced else None,
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
        "Order items:",
    ]
    for item in clean_items:
        price_text = f" - Rs.{item['unit_price']:.2f} each" if item["unit_price"] is not None else " - price to be confirmed"
        lines.append(f"- {item['product_name']} ({item['variant']}) x {item['quantity']}{price_text}")
    lines.extend([
        "",
        f"Order total (excl. delivery charges): Rs.{total:.2f}" if not has_unpriced else "Order total: To be confirmed (excl. delivery charges)",
    ])
    if notes:
        lines.extend(["", f"Additional notes: {notes}"])
    lines.extend(["", "Please confirm availability, delivery charges, and tentative delivery date."])
    whatsapp_url = f"https://wa.me/{WHATSAPP_NUMBER}?text={quote(chr(10).join(lines))}"
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
    return render_template(
        "admin_dashboard.html",
        orders=orders,
        selected_status=status,
        search=search,
        csrf_token=session.get("csrf_token"),
    )


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
    if status not in VALID_ORDER_STATUSES:
        flash("Invalid order status.", "error")
        return redirect(url_for("admin_order_detail", order_id=order_id))
    update_order(order_id, status=status, delivery_date=delivery_date, remarks=remarks)
    flash("Order updated.", "success")
    return redirect(url_for("admin_order_detail", order_id=order_id))


@app.post("/admin/orders/<int:order_id>/status")
@admin_required
def admin_order_quick_status(order_id):
    if request.form.get("csrf_token") != session.get("csrf_token"):
        return "Invalid request token", 400
    status = request.form.get("status", "")
    if status not in VALID_ORDER_STATUSES:
        flash("Invalid order status.", "error")
        return redirect(url_for("admin_dashboard"))
    existing = get_order(order_id)
    if not existing:
        flash("Order not found.", "error")
        return redirect(url_for("admin_dashboard"))
    update_order(
        order_id,
        status=status,
        delivery_date=existing.get("tentative_delivery_date"),
        remarks=existing.get("admin_remarks") or "",
    )
    flash(f"Order {existing['order_number']} status updated to {status}.", "success")
    return redirect(url_for("admin_dashboard"))


@app.post("/admin/orders/<int:order_id>/delete")
@admin_required
def admin_order_delete(order_id):
    if request.form.get("csrf_token") != session.get("csrf_token"):
        return "Invalid request token", 400
    existing = get_order(order_id)
    if not existing:
        flash("Order not found.", "error")
        return redirect(url_for("admin_dashboard"))
    delete_order(order_id)
    flash(f"Order {existing['order_number']} deleted.", "success")
    return redirect(url_for("admin_dashboard"))


@app.get("/health")
def health():
    return jsonify(status="ok", app="Renukambal Home Foods")


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=int(os.environ.get("PORT", "5000")),
        debug=os.environ.get("FLASK_DEBUG", "1") == "1",
    )