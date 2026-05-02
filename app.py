import csv
from flask import Response
from io import StringIO
import os
import requests
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from functools import wraps
from flask_migrate import Migrate
from flask import Flask, flash, jsonify, redirect, render_template, request, url_for
from flask_login import LoginManager, UserMixin, current_user, login_required, login_user, logout_user
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, text
from sqlalchemy.orm import joinedload
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from werkzeug.security import check_password_hash, generate_password_hash


basedir = os.path.abspath(os.path.dirname(__file__))
instance_path = os.path.join(basedir, "instance")
os.makedirs(instance_path, exist_ok=True)

app = Flask(
    __name__,
    static_folder="templates/static",
    static_url_path="/static",
)

app.secret_key = os.environ.get("SECRET_KEY", "fallback_secret")

database_url = os.getenv("DATABASE_URL")
local_db_filename = os.getenv("LOCAL_DB_FILENAME", "inventory.db")
local_db_path = os.path.join(instance_path, local_db_filename)

if database_url:
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
else:
    # SAFE fallback for local only
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + local_db_path

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message_category = "warning"

# Same categories as inventory / add-edit templates
CATEGORIES = [
    "Bits & Disc",
    "Hand Tools",
    "Concreting & Masonry",
    "Nail, Tox, & Screws",
    "Wood Products",
    "Rebars & G.I Wires",
    "Drywall & Ceiling",
]

DEFAULT_SYSTEM_EMAIL = "overpassconstructionsupply@gmail.com"


# ------------------------------
# MODELS
# ------------------------------


class Supplier(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    contact = db.Column(db.String(50), nullable=True)
    address = db.Column(db.String(200), nullable=True)
    email = db.Column(db.String(255), nullable=True)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False,
                         unique=True, index=True)
    email = db.Column(db.String(255), nullable=True, unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False,
                           default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Material(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(120), default="")
    quantity = db.Column(db.Float, default=0.0)
    unit = db.Column(db.String(50), default="pcs")
    price_per_unit = db.Column(db.Float, default=0.0)
    reorder_point = db.Column(db.Float, default=0.0)
    supplier_id = db.Column(
        db.Integer, db.ForeignKey("supplier.id"), nullable=True)
    dismiss_notification = db.Column(db.Boolean, default=False)

    supplier = db.relationship("Supplier", backref="materials")
    variants = db.relationship(
        "MaterialVariant",
        backref="material",
        cascade="all, delete-orphan",
        order_by="MaterialVariant.id",
    )
    reorder_requests = db.relationship(
        "ReorderRequest",
        backref="material",
        cascade="all, delete-orphan",
    )


@app.route("/reorder/<int:reorder_id>/receive", methods=["POST"])
def receive_reorder(reorder_id):
    reorder = ReorderRequest.query.get_or_404(reorder_id)
    reorder.mark_received()
    flash(f"Reorder for '{reorder.material_ref.name}' received!", "success")
    return redirect(url_for("notifications"))


def mark_received(self):
    self.status = "Received"
    self.dismissed = True


class MaterialVariant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    material_id = db.Column(db.Integer, db.ForeignKey(
        "material.id"), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    quantity = db.Column(db.Float, default=0.0)
    unit = db.Column(db.String(50), default="pcs")
    price = db.Column(db.Float, default=0.0)


class Sale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    total = db.Column(db.Float, default=0.0)

    items = db.relationship(
        "SaleItem",
        backref="sale",
        cascade="all, delete-orphan",
        order_by="SaleItem.id",
    )


class SaleItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey("sale.id"), nullable=False)
    material_id = db.Column(db.Integer, db.ForeignKey(
        "material.id"), nullable=False)
    variant_id = db.Column(db.Integer, db.ForeignKey(
        "material_variant.id"), nullable=True)
    qty = db.Column(db.Float, nullable=False)
    price = db.Column(db.Float, nullable=False)

    material = db.relationship("Material", backref="sale_items")
    variant = db.relationship("MaterialVariant", backref="sale_items")

    @property
    def display_name(self):
        if self.variant_id and self.variant:
            return f"{self.material.name} — {self.variant.name}"
        return self.material.name


class ReorderRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    material_id = db.Column(db.Integer, db.ForeignKey(
        "material.id"), nullable=False)
    variant_id = db.Column(db.Integer, db.ForeignKey(
        "material_variant.id"), nullable=True)
    supplier_id = db.Column(
        db.Integer, db.ForeignKey("supplier.id"), nullable=True)
    quantity = db.Column(db.Float, default=0.0)
    notes = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default="Pending")
    dismissed = db.Column(db.Boolean, default=False)  # ✅ ADD THIS

    variant = db.relationship("MaterialVariant", backref="reorder_requests")


# ------------------------------
# HELPERS
# ------------------------------


def _parse_float(val, default=0.0):
    if val is None or val == "":
        return default
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _parse_int_optional(val):
    if val is None or val == "":
        return None
    try:
        return int(val)
    except (TypeError, ValueError):
        return None


def material_is_low_stock(m):
    if m.variants:
        return any(v.quantity <= m.reorder_point for v in m.variants)
    return m.quantity <= m.reorder_point


def _auto_create_reorder_request_if_needed(material, variant=None):
    """
    Automatically create a ReorderRequest when quantity drops below reorder_point.
    Only creates if there's no existing Pending or Ordered request.
    """
    if not material or material.reorder_point <= 0:
        return

    # Reset dismiss flag if quantity goes back above threshold
    current_qty = variant.quantity if variant else material.quantity
    if current_qty > material.reorder_point:
        material.dismiss_notification = False
        return

    # Check if quantity is now below threshold
    if current_qty > material.reorder_point:
        return

    # Check if there's already an active request (Pending or Ordered)
    existing = ReorderRequest.query.filter(
        ReorderRequest.material_id == material.id,
        ReorderRequest.variant_id == (variant.id if variant else None),
        ReorderRequest.status.in_(["Pending", "Ordered"]),
        ReorderRequest.dismissed == False
    ).first()

    if existing:
        return

    # Create new auto-generated reorder request
    # Use supplier from material if available
    default_qty = max(material.reorder_point - current_qty, 1.0)

    new_request = ReorderRequest(
        material_id=material.id,
        variant_id=variant.id if variant else None,
        supplier_id=material.supplier_id,
        quantity=default_qty,
        notes="Auto-generated: Stock fell below reorder point",
        status="Pending",
        dismissed=False
    )
    db.session.add(new_request)


def count_low_notifications():
    count = 0
    materials = Material.query.all()

    for m in materials:
        # Skip if NOT low stock or already dismissed.
        if not material_is_low_stock(m) or m.dismiss_notification:
            continue

        count += 1

    return count


def count_pending_notifications():
    count = 0
    pending_requests = (
        ReorderRequest.query
        .filter_by(status="Pending", dismissed=False)
        .options(joinedload(ReorderRequest.material))
        .all()
    )

    for req in pending_requests:
        m = req.material
        if not m:
            continue
        # Keep navbar count aligned with rows shown on /notifications.
        if m.dismiss_notification:
            continue
        if not material_is_low_stock(m):
            continue
        count += 1

    return count


@app.context_processor
def inject_notification_counts():
    if not current_user.is_authenticated:
        return dict(low_stock_count=0, pending_order_count=0)

    # Red bubble: low stock
    low_stock_count = count_low_notifications()

    # Yellow bubble: pending reorder requests
    pending_order_count = count_pending_notifications()

    return dict(
        low_stock_count=low_stock_count,
        pending_order_count=pending_order_count
    )


def build_low_stock_rows():
    rows = []

    for m in Material.query.order_by(Material.name).all():

        # Skip if NOT low stock or already dismissed.
        if not material_is_low_stock(m) or m.dismiss_notification:
            continue

        total = (
            sum(v.quantity for v in m.variants)
            if m.variants else m.quantity
        )

        row = type("LowRow", (), {})()
        row.id = m.id
        row.name = m.name
        row.qty = total
        row.unit = m.unit
        row.pred_days = None
        row.reorder_requests = ReorderRequest.query.filter_by(
            material_id=m.id,
            dismissed=False
        ).all()

        rows.append(row)

    return rows


def _material_total_quantity(material):
    if material.variants:
        return sum(v.quantity for v in material.variants)
    return material.quantity


def _sort_materials_for_quick_inventory(materials):
    return sorted(
        materials,
        key=lambda m: (
            not material_is_low_stock(m),
            (m.name or "").lower(),
        ),
    )


def inventory_json_payload():
    out = []
    materials = _sort_materials_for_quick_inventory(
        Material.query.options(joinedload(Material.variants)).all()
    )
    for m in materials:
        out.append(
            {
                "id": m.id,
                "name": m.name,
                "quantity": m.quantity,
                "unit": m.unit,
                "reorder_point": m.reorder_point,
                "variants": (
                    [
                        {
                            "id": v.id,
                            "name": v.name,
                            "quantity": v.quantity,
                            "price": v.price
                        }
                        for v in m.variants
                    ]
                    if m.variants
                    else None
                ),
            }
        )
    return out


def _save_material_from_form(material, is_new):
    if not material:
        return

    names = request.form.getlist("variant_name[]")
    qtys = request.form.getlist("variant_quantity[]")
    units = request.form.getlist("variant_unit[]")
    prices = request.form.getlist("variant_price[]")

    variant_rows = []
    for i, name in enumerate(names):
        name = (name or "").strip()
        if not name:
            continue

        q = _parse_float(qtys[i] if i < len(qtys) else 0, 0.0)
        u = (units[i] if i < len(units) else "pcs") or "pcs"
        p = _parse_float(prices[i] if i < len(prices) else 0, 0.0)

        variant_rows.append((name, q, u, p))

    existing_variants = {v.name: v for v in material.variants}

    if variant_rows:
        # IMPORTANT: sync mode (variants control stock)
        material.quantity = 0.0

        used_names = set()

        for name, q, u, p in variant_rows:
            used_names.add(name)

            if name in existing_variants:
                v = existing_variants[name]
                v.quantity = q
                v.unit = u
                v.price = p
                # Auto-check for reorder when variant quantity changes
                _auto_create_reorder_request_if_needed(material, v)
            else:
                db.session.add(
                    MaterialVariant(
                        material_id=material.id,
                        name=name,
                        quantity=q,
                        unit=u,
                        price=p,
                    )
                )
                # New variant will be auto-checked after flush

        # 🔥 DELETE removed variants (VERY IMPORTANT FIX)
        for name, v in existing_variants.items():
            if name not in used_names:
                db.session.delete(v)

    else:
        # fallback: no variants = use main stock
        material.quantity = _parse_float(request.form.get("quantity"), 0.0)

        # Auto-check for reorder when main material quantity changes
        _auto_create_reorder_request_if_needed(material)

        # 🔥 optional cleanup: remove all variants if switching back
        for v in material.variants:
            db.session.delete(v)


# ------------------------------
# WEATHER FEATURE (FIXED)
# ------------------------------

def get_weather():
    try:
        API_KEY = os.environ.get("OPENWEATHER_API_KEY")

        url = f"https://api.openweathermap.org/data/2.5/forecast?q=Quezon City,PH&appid={API_KEY}&units=metric"
        response = requests.get(url)

        print("STATUS:", response.status_code)

        data = response.json()

        if str(data.get("cod")) != "200":
            print("API ERROR:", data)
            return None

        return data

    except Exception as e:
        print("WEATHER ERROR:", e)
        return None


def _linear_regression_predict(x_values, y_values, predict_x):
    """Fit y = mx + b via least squares and predict y at predict_x."""
    n = len(x_values)
    if n == 0:
        return 0.0

    x_mean = sum(x_values) / n
    y_mean = sum(y_values) / n

    numerator = 0.0
    denominator = 0.0
    for x, y in zip(x_values, y_values):
        dx = x - x_mean
        numerator += dx * (y - y_mean)
        denominator += dx * dx

    if denominator == 0:
        return y_mean

    slope = numerator / denominator
    intercept = y_mean - (slope * x_mean)
    return (slope * predict_x) + intercept


def _reset_serializer():
    return URLSafeTimedSerializer(app.secret_key)


def _build_password_reset_link(user):
    token = _reset_serializer().dumps(
        {"user_id": user.id, "email": user.email},
        salt="password-reset",
    )
    base_url = os.environ.get("APP_BASE_URL", "").rstrip("/")
    if base_url:
        return f"{base_url}/reset-password/{token}"
    return url_for("reset_password", token=token, _external=True)


def _send_password_reset_email(target_email, reset_link):
    subject = "Password Reset Instructions"
    body = (
        "Forgotten your password?\n\n"
        "Click the link below to set a new password:\n"
        f"{reset_link}\n\n"
        "If you did not request this, you can ignore this email."
    )

    smtp_host = os.environ.get("SMTP_HOST")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_username = os.environ.get("SMTP_USERNAME", DEFAULT_SYSTEM_EMAIL)
    smtp_password = os.environ.get("SMTP_PASSWORD")
    smtp_use_tls = os.environ.get(
        "SMTP_USE_TLS", "true").lower() in ("1", "true", "yes")
    mail_from = os.environ.get(
        "MAIL_FROM", DEFAULT_SYSTEM_EMAIL) or smtp_username

    if not smtp_host or not mail_from:
        return False

    message = MIMEText(body)
    message["Subject"] = subject
    message["From"] = mail_from
    message["To"] = target_email

    with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as smtp:
        if smtp_use_tls:
            smtp.starttls()
        if smtp_username and smtp_password:
            smtp.login(smtp_username, smtp_password)
        smtp.sendmail(mail_from, [target_email], message.as_string())
    return True


def _send_reorder_email(material, supplier, quantity, notes, variant=None):
    smtp_host = os.environ.get("SMTP_HOST")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_username = os.environ.get("SMTP_USERNAME", DEFAULT_SYSTEM_EMAIL)
    smtp_password = os.environ.get("SMTP_PASSWORD")
    smtp_use_tls = os.environ.get(
        "SMTP_USE_TLS", "true").lower() in ("1", "true", "yes")
    mail_from = os.environ.get(
        "MAIL_FROM", DEFAULT_SYSTEM_EMAIL) or smtp_username

    if not smtp_host or not mail_from:
        return False, "SMTP is not configured."
    if not supplier.email:
        return False, "Supplier email is missing."

    subject = f"Purchase Order Request - {material.name}"
    body_lines = [
        f"Hello {supplier.name},",
        "",
        "Please process this reorder request:",
        f"- Material: {material.name}",
        f"- Variant: {variant.name if variant else 'N/A'}",
        f"- Quantity: {quantity} {material.unit or 'pcs'}",
    ]
    if notes:
        body_lines.extend(["", f"Notes: {notes}"])
    body_lines.extend(["", "Thank you."])
    body = "\n".join(body_lines)

    message = MIMEText(body)
    message["Subject"] = subject
    message["From"] = mail_from
    message["To"] = supplier.email

    with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as smtp:
        if smtp_use_tls:
            smtp.starttls()
        if smtp_username and smtp_password:
            smtp.login(smtp_username, smtp_password)
        smtp.sendmail(mail_from, [supplier.email], message.as_string())
    return True, ""


def analyze_weather(data):
    weather_list = data.get("list", [])
    total_count = len(weather_list)
    if total_count == 0:
        return ["No forecast data available for analysis."]

    # x = time index (3-hour forecast slots), y = rain signal (0 or 1)
    x_values = []
    y_values = []
    for idx, item in enumerate(weather_list):
        weather_main = (item.get("weather") or [{}])[0].get("main", "").lower()
        rain_like = 1.0 if any(k in weather_main for k in (
            "rain", "drizzle", "thunderstorm")) else 0.0
        x_values.append(float(idx))
        y_values.append(rain_like)

    # Predict rain risk for the next 24 hours (8 x 3-hour slots)
    future_points = min(8, total_count)
    predicted = []
    for step in range(future_points):
        px = float(total_count + step)
        py = _linear_regression_predict(x_values, y_values, px)
        predicted.append(max(0.0, min(1.0, py)))

    y = (sum(predicted) / len(predicted)) if predicted else 0.0

    suggestions = []

    if y > 0.6:
        suggestions.append(
            "Linear regression forecast: high rain risk in the next 24 hours.")
        suggestions.append("Reduce outdoor material orders by around 30-50%.")
        suggestions.append(
            "Prioritize covered storage for cement, sand, CHB, and wood products.")

    elif y > 0.3:
        suggestions.append(
            "Linear regression forecast: moderate rain risk in the next 24 hours.")
        suggestions.append(
            "Reduce outdoor material orders moderately (around 15-25%).")

    else:
        suggestions.append(
            "Linear regression forecast: low rain risk in the next 24 hours.")
        suggestions.append("Maintain standard inventory levels.")

    suggestions.append(f"Predicted rain risk score: {y:.2f}")

    return suggestions


def build_weather_days(data, max_days=5):
    by_day = {}

    for item in data.get("list", []):
        ts = item.get("dt")
        if not ts:
            continue

        dt_obj = datetime.fromtimestamp(ts)
        day_key = dt_obj.strftime("%Y-%m-%d")
        condition = (
            (item.get("weather") or [{}])[0].get("main", "Unknown")
            if isinstance(item.get("weather"), list)
            else "Unknown"
        )
        temp = item.get("main", {}).get("temp")

        if day_key not in by_day:
            by_day[day_key] = {
                "date_obj": dt_obj,
                "temps": [],
                "conditions": {},
            }

        if temp is not None:
            by_day[day_key]["temps"].append(float(temp))

        by_day[day_key]["conditions"][condition] = (
            by_day[day_key]["conditions"].get(condition, 0) + 1
        )

    days = []
    for day in sorted(by_day.keys())[:max_days]:
        day_data = by_day[day]
        temps = day_data["temps"]
        conditions = day_data["conditions"]

        top_condition = "Unknown"
        if conditions:
            top_condition = max(conditions.items(), key=lambda x: x[1])[0]

        days.append(
            {
                "day_name": day_data["date_obj"].strftime("%a"),
                "date_label": day_data["date_obj"].strftime("%b %d"),
                "min_temp": round(min(temps), 1) if temps else None,
                "max_temp": round(max(temps), 1) if temps else None,
                "condition": top_condition,
            }
        )

    return days


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def admin_required(func):
    @wraps(func)
    @login_required
    def wrapped(*args, **kwargs):
        if not current_user.is_admin:
            flash("Admin access required.", "danger")
            return redirect(url_for("index"))
        return func(*args, **kwargs)

    return wrapped


@app.before_request
def require_login_for_pos():
    public_endpoints = {"login", "register",
                        "forgot_password", "reset_password", "static"}
    endpoint = request.endpoint

    if endpoint is None:
        return None

    if endpoint.startswith("static"):
        return None

    if endpoint in public_endpoints:
        return None

    if current_user.is_authenticated:
        return None

    if request.path == "/checkout":
        return jsonify(success=False, message="Please log in first."), 401

    return redirect(url_for("login", next=request.url))
# ------------------------------
# ROUTES
# ------------------------------


@app.route("/")
def home():
    return redirect(url_for("login"))


@app.route("/pos")
@login_required
def index():
    materials = _sort_materials_for_quick_inventory(
        Material.query.options(joinedload(Material.variants)).all()
    )

    weather_data = get_weather()

    if not weather_data:
        warning = "Weather data not available. Check API key or internet connection."
        advice = []
        weather_days = []
    else:
        warning = None
        advice = analyze_weather(weather_data)
        weather_days = build_weather_days(weather_data)

    return render_template(
        "index.html",
        materials=materials,
        weather=weather_data,
        warning=warning,
        advice=advice,
        weather_days=weather_days,
    )


@app.route("/checkout", methods=["POST"])
@login_required
def checkout():
    data = request.get_json(silent=True) or {}
    cart = data.get("cart") or []
    if not cart:
        return jsonify(success=False, message="Cart is empty"), 400

    total = sum(
        float(item.get("price", 0)) * float(item.get("qty", 0))
        for item in cart
    )

    for item in cart:
        mid = int(item["id"])
        qty = float(item.get("qty", 0))
        if qty <= 0:
            return jsonify(success=False, message="Invalid quantity"), 400
        vid = item.get("variantId")
        if vid is not None and vid != "":
            vid = int(vid)
        else:
            vid = None

        m = Material.query.options(joinedload(Material.variants)).get(mid)
        if not m:
            return jsonify(success=False, message=f"Material {mid} not found"), 400

        if vid:
            v = MaterialVariant.query.filter_by(
                id=vid, material_id=m.id).first()
            if not v:
                return jsonify(success=False, message="Invalid variant"), 400
            if v.quantity < qty:
                return jsonify(
                    success=False,
                    message=f"Not enough stock for {m.name} ({v.name})",
                ), 400
        else:
            if m.variants:
                return jsonify(
                    success=False,
                    message=f"Select a variant for {m.name}",
                ), 400
            if m.quantity < qty:
                return jsonify(success=False, message=f"Not enough stock for {m.name}"), 400

    sale = Sale(total=total)
    db.session.add(sale)
    db.session.flush()

    auto_reordered_items = []

    for item in cart:
        mid = int(item["id"])
        qty = float(item.get("qty", 0))
        price = float(item.get("price", 0))
        vid = item.get("variantId")
        if vid is not None and vid != "":
            vid = int(vid)
        else:
            vid = None

        m = Material.query.get(mid)
        si = SaleItem(
            sale_id=sale.id,
            material_id=mid,
            variant_id=vid,
            qty=qty,
            price=price,
        )
        db.session.add(si)

        if vid:
            v = MaterialVariant.query.get(vid)
            v.quantity -= qty
            # Check if this triggers auto-reorder
            was_above = (float(v.quantity or 0.0) + qty) > m.reorder_point
            is_below = v.quantity <= m.reorder_point
            if was_above and is_below:
                auto_reordered_items.append(f"{m.name} - {v.name}")
            _auto_create_reorder_request_if_needed(m, v)
        else:
            m.quantity -= qty
            # Check if this triggers auto-reorder
            was_above = (float(m.quantity or 0.0) + qty) > m.reorder_point
            is_below = m.quantity <= m.reorder_point
            if was_above and is_below:
                auto_reordered_items.append(m.name)
            _auto_create_reorder_request_if_needed(m)

    print(data)
    print(cart)

    db.session.commit()

    response = {
        "success": True,
        "updated_inventory": inventory_json_payload()
    }
    if auto_reordered_items:
        response["auto_reordered"] = auto_reordered_items
        response["message"] = f"Reorder notifications created for: {', '.join(auto_reordered_items)}"

    return jsonify(response)


@app.route("/inventory")
@login_required
def inventory():
    materials = Material.query.options(joinedload(Material.variants)).all()
    return render_template("inventory.html", materials=materials)


@app.route("/material/add", methods=["GET", "POST"])
@login_required
def add_material():
    suppliers = Supplier.query.order_by(Supplier.name).all()

    if request.method == "POST":

        m = Material(
            name=request.form.get("name"),
            category=request.form.get("category"),
            unit=request.form.get("unit", "pcs"),
            reorder_point=_parse_float(request.form.get("reorder_point")),
            price_per_unit=_parse_float(request.form.get("price_per_unit")),
            supplier_id=_parse_int_optional(request.form.get("supplier_id"))
        )

        db.session.add(m)
        db.session.flush()

        _save_material_from_form(m, is_new=True)

        db.session.commit()

        flash(f"Material '{m.name}' added.", "success")
        return redirect(url_for("inventory"))

    return render_template(
        "add_edit_material.html",
        material=None,
        categories=CATEGORIES,
        suppliers=suppliers,
    )


@app.route("/material/edit/<int:id>", methods=["GET", "POST"])
@login_required
def edit_material(id):
    material = Material.query.options(
        joinedload(Material.variants)
    ).get_or_404(id)

    suppliers = Supplier.query.order_by(Supplier.name).all()

    if request.method == "POST":
        print("EDIT FORM RECEIVED:", request.form)

        material.name = request.form.get("name", material.name)
        material.category = request.form.get("category", material.category)
        material.unit = request.form.get("unit", material.unit)

        material.reorder_point = _parse_float(
            request.form.get("reorder_point"),
            material.reorder_point
        )

        material.supplier_id = _parse_int_optional(
            request.form.get("supplier_id"))

        _save_material_from_form(material, is_new=False)

        db.session.commit()

        flash("Material updated successfully.", "success")
        return redirect(url_for("inventory"))

    return render_template(
        "add_edit_material.html",
        material=material,
        categories=CATEGORIES,
        suppliers=suppliers,
    )


@app.route("/material/delete/<int:id>", methods=["POST"])
@login_required
def delete_material(id):
    material = Material.query.options(
        joinedload(Material.variants),
        joinedload(Material.sale_items)
    ).get_or_404(id)

    if material.sale_items:
        flash("Cannot delete a material that appears in sales history.", "danger")
        return redirect(url_for("inventory"))

    for v in material.variants:
        db.session.delete(v)

    db.session.delete(material)
    db.session.commit()

    flash("Material deleted.", "success")
    return redirect(url_for("inventory"))


@app.route("/reorder/<int:material_id>", methods=["GET", "POST"])
@login_required
def reorder(material_id):
    material = Material.query.get_or_404(material_id)
    suppliers = Supplier.query.order_by(Supplier.name).all()
    if request.method == "POST":
        sid = _parse_int_optional(request.form.get("supplier_id"))
        if sid is None:
            flash("Please select a supplier.", "danger")
            return redirect(url_for("reorder", material_id=material_id))
        supplier = Supplier.query.get_or_404(sid)
        if not (supplier.email or "").strip():
            flash("Selected supplier does not have an email address yet.", "danger")
            return redirect(url_for("reorder", material_id=material_id))
        qty = _parse_float(request.form.get("quantity"), 0.0)
        if qty <= 0:
            flash("Order quantity must be greater than zero.", "danger")
            return redirect(url_for("reorder", material_id=material_id))
        variant_id = _parse_int_optional(request.form.get("variant_id"))
        selected_variant = None
        if material.variants:
            if variant_id is None:
                flash("Please select a variant for this material.", "danger")
                return redirect(url_for("reorder", material_id=material_id))
            selected_variant = MaterialVariant.query.filter_by(
                id=variant_id, material_id=material.id
            ).first()
            if not selected_variant:
                flash("Invalid variant selected.", "danger")
                return redirect(url_for("reorder", material_id=material_id))
        notes = (request.form.get("notes") or "").strip()
        rr = ReorderRequest(
            material_id=material.id,
            variant_id=variant_id if selected_variant else None,
            supplier_id=sid,
            quantity=qty,
            notes=notes or None,
            status="Pending",
        )
        db.session.add(rr)
        db.session.commit()
        try:
            sent, reason = _send_reorder_email(
                material, supplier, qty, notes, variant=selected_variant
            )
            if sent:
                flash(
                    f"Reorder request recorded and email sent to {supplier.name}.", "success")
            elif reason == "SMTP is not configured.":
                flash("Reorder request recorded successfully.", "success")
                flash(
                    "Supplier email was not sent: this deployment has no SMTP settings "
                    "(SMTP_HOST, MAIL_FROM, etc.). Configure them on the host if you want automatic emails.",
                    "info",
                )
            else:
                flash(
                    f"Reorder request recorded, but email was not sent ({reason}).",
                    "warning",
                )
        except Exception as e:
            print("EMAIL ERROR:", str(e))  # shows in Render logs
            flash(
                f"Reorder request recorded, but email failed: {str(e)}", "warning")
        return redirect(url_for("inventory"))
    return render_template("reorder.html", material=material, suppliers=suppliers)


@app.route("/reorder/request/<int:id>/status", methods=["POST"])
@login_required
def update_reorder_status(id):
    rr = ReorderRequest.query.get_or_404(id)
    status = request.form.get("status", "").strip()
    if status not in ("Ordered", "Received", "Pending"):
        flash("Invalid status.", "danger")
        return redirect(url_for("notifications"))
    previous_status = rr.status
    rr.status = status

    # When a reorder is received, add the ordered quantity to stock once.
    if status == "Received" and previous_status != "Received":
        material = rr.material
        variant = rr.variant
        added_qty = float(rr.quantity or 0.0)
        if added_qty > 0:
            if variant:
                variant.quantity = float(variant.quantity or 0.0) + added_qty
                # Check if still below reorder point after receiving
                _auto_create_reorder_request_if_needed(material, variant)
            elif material:
                material.quantity = float(material.quantity or 0.0) + added_qty
                # Check if still below reorder point after receiving
                _auto_create_reorder_request_if_needed(material)

    db.session.commit()
    if status == "Received" and previous_status != "Received":
        unit_label = (
            (rr.variant.unit if rr.variant else (
                rr.material.unit if rr.material else ""))
            or ""
        )
        item_name = rr.material.name if rr.material else "material"
        if rr.variant:
            item_name = f"{item_name} - {rr.variant.name}"
        flash(
            f"Reorder received. Added {rr.quantity} {unit_label} to {item_name} inventory.",
            "success",
        )
    else:
        flash("Reorder status updated.", "success")
    return redirect(url_for("notifications"))


@app.route("/notifications")
@login_required
def notifications():
    low = build_low_stock_rows()
    pending_reorders = (
        ReorderRequest.query
        .filter_by(status="Pending", dismissed=False)
        .options(
            joinedload(ReorderRequest.material),
            joinedload(ReorderRequest.variant),
        )
        .order_by(ReorderRequest.id.desc())
        .all()
    )

    return render_template(
        "notifications.html",
        low=low,
        pending_reorders=pending_reorders,
    )


@app.route("/sales")
@login_required
def sales():
    sales_list = (
        Sale.query.options(joinedload(
            Sale.items).joinedload(SaleItem.material))
        .order_by(Sale.date.desc())
        .all()
    )
    return render_template("sales.html", sales=sales_list)


@app.route("/sales/<int:id>")
@login_required
def sale_view(id):
    sale = (
        Sale.query.options(
            joinedload(Sale.items).joinedload(SaleItem.material),
            joinedload(Sale.items).joinedload(SaleItem.variant),
        )
        .filter_by(id=id)
        .first_or_404()
    )
    return render_template("sale_view.html", sale=sale)


@app.route("/sales/clear", methods=["POST"])
@login_required
def clear_sales():
    SaleItem.query.delete()
    Sale.query.delete()
    db.session.commit()
    flash("All sales records were cleared.", "success")
    return redirect(url_for("sales"))


@app.route("/sales/export")
@login_required
def export_sales_csv():
    # Query all sales with items
    sales_list = (
        Sale.query.options(joinedload(Sale.items).joinedload(SaleItem.material),
                           joinedload(Sale.items).joinedload(SaleItem.variant))
        .order_by(Sale.date.desc())
        .all()
    )

    # Prepare CSV
    si = StringIO()
    writer = csv.writer(si)

    # Header row
    writer.writerow([
        "Sale ID", "Date", "Total (₱)", "Item Name", "Variant", "Quantity", "Price per Unit", "Subtotal"
    ])

    # Data rows
    for sale in sales_list:
        for item in sale.items:
            writer.writerow([
                sale.id,
                sale.date.strftime("%Y-%m-%d %H:%M:%S"),
                "%.2f" % sale.total,
                item.material.name,
                item.variant.name if item.variant else "",
                item.qty,
                "%.2f" % item.price,
                "%.2f" % (item.price * item.qty),
            ])

    output = si.getvalue()
    si.close()

    # Send as downloadable CSV
    return Response(
        output,
        mimetype="text/csv",
        headers={
            "Content-Disposition": f"attachment;filename=sales_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"}
    )


@app.route("/notifications/dismiss/<int:material_id>")
@login_required
def dismiss_notification(material_id):
    material = Material.query.get_or_404(material_id)

    # Persist dismissal for low-stock notifications tied to the material.
    material.dismiss_notification = True

    # Get ALL reorder requests for this material
    requests = ReorderRequest.query.filter_by(
        material_id=material_id,
        dismissed=False
    ).all()

    # Mark them as dismissed
    for r in requests:
        r.dismissed = True

    db.session.commit()

    return redirect(url_for("notifications"))


@app.route("/suppliers", methods=["GET", "POST"])
@login_required
def suppliers():
    if request.method == "POST":
        name = request.form["name"]
        contact = request.form["contact"]
        address = request.form["address"]
        email = (request.form.get("email") or "").strip()
        new_supplier = Supplier(
            name=name,
            contact=contact,
            address=address,
            email=email or None,
        )
        db.session.add(new_supplier)
        db.session.commit()
        flash(f"Supplier '{name}' added successfully!", "success")
        return redirect(url_for("suppliers"))

    suppliers_list = Supplier.query.all()
    return render_template("suppliers.html", suppliers=suppliers_list)


@app.route("/supplier/edit/<int:id>", methods=["GET", "POST"])
@login_required
def edit_supplier(id):
    supplier = Supplier.query.get_or_404(id)
    if request.method == "POST":
        supplier.name = request.form["name"]
        supplier.contact = request.form["contact"]
        supplier.address = request.form["address"]
        supplier.email = (request.form.get("email") or "").strip() or None
        db.session.commit()
        flash(f"Supplier '{supplier.name}' updated successfully!", "success")
        return redirect(url_for("suppliers"))
    return render_template("edit_supplier.html", supplier=supplier)


@app.route("/supplier/delete/<int:id>", methods=["POST"])
@login_required
def delete_supplier(id):
    supplier = Supplier.query.get_or_404(id)
    db.session.delete(supplier)
    db.session.commit()
    flash(f"Supplier '{supplier.name}' deleted successfully!", "success")
    return redirect(url_for("suppliers"))


@app.route("/about")
@login_required
def about():
    return render_template("about.html")


@app.route("/settings")
@admin_required
def settings():
    users = User.query.order_by(User.created_at.desc()).all()
    sales_rows = Sale.query.order_by(Sale.date.desc()).all()
    monthly_map = {}
    for sale in sales_rows:
        month_key = sale.date.strftime("%Y-%m")
        if month_key not in monthly_map:
            monthly_map[month_key] = {
                "month": month_key,
                "count": 0,
                "total": 0.0,
            }
        monthly_map[month_key]["count"] += 1
        monthly_map[month_key]["total"] += float(sale.total or 0.0)

    monthly_sales = sorted(
        monthly_map.values(),
        key=lambda row: row["month"],
        reverse=True
    )
    admin_users = [u for u in users if u.is_admin]
    non_admin_users = [u for u in users if not u.is_admin]

    stats = {
        "users": User.query.count(),
        "admins": User.query.filter_by(is_admin=True).count(),
        "materials": Material.query.count(),
        "suppliers": Supplier.query.count(),
        "sales": Sale.query.count(),
    }
    return render_template(
        "settings.html",
        users=users,
        admin_users=admin_users,
        non_admin_users=non_admin_users,
        monthly_sales=monthly_sales,
        stats=stats,
    )


@app.route("/settings/sales/export-month")
@admin_required
def export_month_sales_csv():
    month = (request.args.get("month") or "").strip()
    try:
        month_start = datetime.strptime(month, "%Y-%m")
    except ValueError:
        flash("Invalid month format.", "danger")
        return redirect(url_for("settings"))

    if month_start.month == 12:
        month_end = datetime(month_start.year + 1, 1, 1)
    else:
        month_end = datetime(month_start.year, month_start.month + 1, 1)

    sales_list = (
        Sale.query.options(
            joinedload(Sale.items).joinedload(SaleItem.material),
            joinedload(Sale.items).joinedload(SaleItem.variant),
        )
        .filter(Sale.date >= month_start, Sale.date < month_end)
        .order_by(Sale.date.asc())
        .all()
    )

    si = StringIO()
    writer = csv.writer(si)
    writer.writerow([
        "Sale ID", "Date", "Total (PHP)", "Item Name", "Variant", "Quantity", "Price per Unit", "Subtotal"
    ])

    for sale in sales_list:
        for item in sale.items:
            writer.writerow([
                sale.id,
                sale.date.strftime("%Y-%m-%d %H:%M:%S"),
                "%.2f" % sale.total,
                item.material.name if item.material else "",
                item.variant.name if item.variant else "",
                item.qty,
                "%.2f" % item.price,
                "%.2f" % (item.price * item.qty),
            ])

    output = si.getvalue()
    si.close()

    filename = f"sales_{month}.csv"
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename={filename}"},
    )


@app.route("/settings/users/<int:user_id>/toggle-admin", methods=["POST"])
@admin_required
def toggle_admin(user_id):
    user = User.query.get_or_404(user_id)
    admin_count = User.query.filter_by(is_admin=True).count()

    if user.id == current_user.id and user.is_admin:
        flash("You cannot remove your own admin access.", "danger")
        return redirect(url_for("settings"))

    if user.is_admin and admin_count <= 1:
        flash("At least one admin account is required.", "danger")
        return redirect(url_for("settings"))

    user.is_admin = not user.is_admin
    db.session.commit()
    flash(
        f"Admin status updated for '{user.username}'.",
        "success",
    )
    return redirect(url_for("settings"))


@app.route("/settings/users/<int:user_id>/delete", methods=["POST"])
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    admin_count = User.query.filter_by(is_admin=True).count()

    if user.id == current_user.id:
        flash("You cannot delete your own account while logged in.", "danger")
        return redirect(url_for("settings"))

    if user.is_admin and admin_count <= 1:
        flash("Cannot delete the last admin account.", "danger")
        return redirect(url_for("settings"))

    username = user.username
    db.session.delete(user)
    db.session.commit()
    flash(f"Account '{username}' deleted.", "success")
    return redirect(url_for("settings"))


@app.route("/settings/users/<int:user_id>/reset-password", methods=["POST"])
@admin_required
def admin_reset_password(user_id):
    user = User.query.get_or_404(user_id)
    new_password = request.form.get("new_password") or ""
    confirm_password = request.form.get("confirm_password") or ""

    if len(new_password) < 6:
        flash("New password must be at least 6 characters.", "danger")
        return redirect(url_for("settings"))

    if new_password != confirm_password:
        flash("Passwords do not match.", "danger")
        return redirect(url_for("settings"))

    user.set_password(new_password)
    db.session.commit()
    flash(f"Password updated for '{user.username}'.", "success")
    return redirect(url_for("settings"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        next_url = request.form.get("next") or url_for("index")

        user = User.query.filter_by(username=username).first()
        if not user or not user.check_password(password):
            flash("Invalid username or password.", "danger")
            return render_template("login.html", next=next_url, username=username)

        login_user(user)
        flash("Logged in successfully.", "success")
        return redirect(next_url)

    return render_template("login.html", next=request.args.get("next", ""))


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        confirm_password = request.form.get("confirm_password") or ""

        if len(username) < 3:
            flash("Username must be at least 3 characters.", "danger")
            return render_template("register.html", username=username, email=email)

        if "@" not in email or "." not in email:
            flash("Please enter a valid email address.", "danger")
            return render_template("register.html", username=username, email=email)

        if len(password) < 6:
            flash("Password must be at least 6 characters.", "danger")
            return render_template("register.html", username=username, email=email)

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template("register.html", username=username, email=email)

        exists = User.query.filter_by(username=username).first()
        if exists:
            flash("Username is already taken.", "danger")
            return render_template("register.html", username=username, email=email)

        email_exists = User.query.filter_by(email=email).first()
        if email_exists:
            flash("Email is already registered.", "danger")
            return render_template("register.html", username=username, email=email)

        new_user = User(
            username=username,
            email=email,
            is_admin=(User.query.count() == 0)
        )
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        flash("Account created. You can now log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        if not email:
            flash("Email is required.", "danger")
            return render_template("forgot_password.html", email=email)

        user = User.query.filter_by(email=email).first()
        if user and user.email:
            reset_link = _build_password_reset_link(user)
            try:
                email_sent = _send_password_reset_email(user.email, reset_link)
                if not email_sent:
                    flash(
                        "SMTP is not configured yet. Set SMTP_HOST, SMTP_PORT, SMTP_USERNAME, "
                        "SMTP_PASSWORD, MAIL_FROM, and APP_BASE_URL in Render.",
                        "warning",
                    )
                    flash(f"Temporary reset link: {reset_link}", "info")
                else:
                    flash("Password reset link sent to your email.", "success")
            except Exception:
                flash("Unable to send email right now. Please try again.", "danger")
                return render_template("forgot_password.html", email=email)

        flash(
            "If that email address exists in our system, we sent password reset instructions.",
            "info",
        )
        return redirect(url_for("login"))

    return render_template("forgot_password.html")


@app.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    try:
        data = _reset_serializer().loads(token, salt="password-reset", max_age=3600)
        user_id = data.get("user_id")
        email = data.get("email")
        user = User.query.get(user_id)
        if not user or user.email != email:
            raise BadSignature("Invalid user token payload")
    except SignatureExpired:
        flash("Password reset link has expired. Please request a new one.", "danger")
        return redirect(url_for("forgot_password"))
    except BadSignature:
        flash("Invalid password reset link.", "danger")
        return redirect(url_for("forgot_password"))

    if request.method == "POST":
        new_password = request.form.get("new_password") or ""
        confirm_password = request.form.get("confirm_password") or ""

        if len(new_password) < 6:
            flash("New password must be at least 6 characters.", "danger")
            return render_template("reset_password.html", token=token)

        if new_password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template("reset_password.html", token=token)

        user.set_password(new_password)
        db.session.commit()
        flash("Password reset successful. Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("reset_password.html", token=token)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


def _migrate_sqlite_schema():
    """Add columns missing from older DB files (create_all does not alter existing tables)."""
    engine = db.engine
    if engine.dialect.name != "sqlite":
        return
    insp = inspect(engine)

    with engine.connect() as conn:
        if insp.has_table("material"):
            material_columns = {c["name"]
                                for c in insp.get_columns("material")}
            material_additions = [
                ("category", "ALTER TABLE material ADD COLUMN category VARCHAR(120) DEFAULT ''"),
                ("unit", "ALTER TABLE material ADD COLUMN unit VARCHAR(50) DEFAULT 'pcs'"),
                ("reorder_point",
                 "ALTER TABLE material ADD COLUMN reorder_point REAL DEFAULT 0"),
                ("supplier_id", "ALTER TABLE material ADD COLUMN supplier_id INTEGER"),
                ("dismiss_notification",
                 "ALTER TABLE material ADD COLUMN dismiss_notification BOOLEAN DEFAULT 0"),
            ]
            for col, stmt in material_additions:
                if col not in material_columns:
                    conn.execute(text(stmt))

        if insp.has_table("reorder_request"):
            reorder_columns = {c["name"]
                               for c in insp.get_columns("reorder_request")}
            reorder_additions = [
                ("quantity", "ALTER TABLE reorder_request ADD COLUMN quantity REAL DEFAULT 0"),
                ("notes", "ALTER TABLE reorder_request ADD COLUMN notes TEXT"),
                ("dismissed", "ALTER TABLE reorder_request ADD COLUMN dismissed BOOLEAN DEFAULT 0"),
                ("variant_id", "ALTER TABLE reorder_request ADD COLUMN variant_id INTEGER"),
            ]
            for col, stmt in reorder_additions:
                if col not in reorder_columns:
                    conn.execute(text(stmt))

            # Older databases stored the requested amount in requested_qty.
            if "requested_qty" in reorder_columns and "quantity" not in reorder_columns:
                conn.execute(text(
                    "UPDATE reorder_request "
                    "SET quantity = COALESCE(requested_qty, 0) "
                    "WHERE quantity IS NULL OR quantity = 0"
                ))

        if insp.has_table("sale_item"):
            sale_item_columns = {c["name"]
                                 for c in insp.get_columns("sale_item")}
            sale_item_additions = [
                ("variant_id", "ALTER TABLE sale_item ADD COLUMN variant_id INTEGER"),
            ]
            for col, stmt in sale_item_additions:
                if col not in sale_item_columns:
                    conn.execute(text(stmt))

        if insp.has_table("user"):
            user_columns = {c["name"] for c in insp.get_columns("user")}
            if "email" not in user_columns:
                conn.execute(
                    text('ALTER TABLE "user" ADD COLUMN email VARCHAR(255)')
                )
            if "is_admin" not in user_columns:
                conn.execute(
                    text('ALTER TABLE "user" ADD COLUMN is_admin BOOLEAN DEFAULT 0')
                )
                conn.execute(
                    text(
                        'UPDATE "user" SET is_admin = 1 '
                        "WHERE id = (SELECT MIN(id) FROM \"user\")"
                    )
                )

        if insp.has_table("supplier"):
            supplier_columns = {c["name"]
                                for c in insp.get_columns("supplier")}
            if "email" not in supplier_columns:
                conn.execute(
                    text("ALTER TABLE supplier ADD COLUMN email VARCHAR(255)")
                )

        conn.commit()


def _migrate_user_auth_schema():
    engine = db.engine
    insp = inspect(engine)
    if not insp.has_table("user"):
        return

    user_columns = {c["name"] for c in insp.get_columns("user")}

    with engine.connect() as conn:
        if "email" not in user_columns:
            conn.execute(
                text('ALTER TABLE "user" ADD COLUMN email VARCHAR(255)'))

        if "is_admin" not in user_columns:
            if engine.dialect.name == "postgresql":
                conn.execute(
                    text('ALTER TABLE "user" ADD COLUMN is_admin BOOLEAN DEFAULT FALSE'))
                conn.execute(
                    text(
                        'UPDATE "user" SET is_admin = TRUE '
                        'WHERE id = (SELECT MIN(id) FROM "user")'
                    )
                )
            else:
                conn.execute(
                    text('ALTER TABLE "user" ADD COLUMN is_admin BOOLEAN DEFAULT 0'))
                conn.execute(
                    text(
                        'UPDATE "user" SET is_admin = 1 '
                        'WHERE id = (SELECT MIN(id) FROM "user")'
                    )
                )

        if insp.has_table("supplier"):
            supplier_columns = {c["name"]
                                for c in insp.get_columns("supplier")}
            if "email" not in supplier_columns:
                conn.execute(
                    text("ALTER TABLE supplier ADD COLUMN email VARCHAR(255)")
                )
        if insp.has_table("reorder_request"):
            reorder_columns = {c["name"]
                               for c in insp.get_columns("reorder_request")}
            if "variant_id" not in reorder_columns:
                conn.execute(
                    text("ALTER TABLE reorder_request ADD COLUMN variant_id INTEGER")
                )
        conn.commit()


# ------------------------------
# DATABASE INIT
# ------------------------------
with app.app_context():
    db.create_all()
    _migrate_user_auth_schema()
    _migrate_sqlite_schema()


# ------------------------------
# RUN APP
# ------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
