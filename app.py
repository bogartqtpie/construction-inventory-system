import csv
from flask import Response
from io import StringIO
import os
import requests
from datetime import datetime
from flask_migrate import Migrate
from flask import Flask, flash, jsonify, redirect, render_template, request, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, text
from sqlalchemy.orm import joinedload


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


# ------------------------------
# MODELS
# ------------------------------


class Supplier(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    contact = db.Column(db.String(50), nullable=True)
    address = db.Column(db.String(200), nullable=True)


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
    supplier_id = db.Column(
        db.Integer, db.ForeignKey("supplier.id"), nullable=True)
    quantity = db.Column(db.Float, default=0.0)
    notes = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default="Pending")
    dismissed = db.Column(db.Boolean, default=False)  # ✅ ADD THIS


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
            _material_total_quantity(m) > m.reorder_point,
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

        # 🔥 DELETE removed variants (VERY IMPORTANT FIX)
        for name, v in existing_variants.items():
            if name not in used_names:
                db.session.delete(v)

    else:
        # fallback: no variants = use main stock
        material.quantity = _parse_float(request.form.get("quantity"), 0.0)

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
# ------------------------------
# ROUTES
# ------------------------------


@app.route("/")
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
        else:
            m.quantity -= qty

    print(data)
    print(cart)

    db.session.commit()

    return jsonify(success=True, updated_inventory=inventory_json_payload())


@app.route("/inventory")
def inventory():
    materials = Material.query.options(joinedload(Material.variants)).all()
    return render_template("inventory.html", materials=materials)


@app.route("/material/add", methods=["GET", "POST"])
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
def reorder(material_id):
    material = Material.query.get_or_404(material_id)
    suppliers = Supplier.query.order_by(Supplier.name).all()
    if request.method == "POST":
        sid = _parse_int_optional(request.form.get("supplier_id"))
        if sid is None:
            flash("Please select a supplier.", "danger")
            return redirect(url_for("reorder", material_id=material_id))
        qty = _parse_float(request.form.get("quantity"), 0.0)
        if qty <= 0:
            flash("Order quantity must be greater than zero.", "danger")
            return redirect(url_for("reorder", material_id=material_id))
        notes = (request.form.get("notes") or "").strip()
        rr = ReorderRequest(
            material_id=material.id,
            supplier_id=sid,
            quantity=qty,
            notes=notes or None,
            status="Pending",
        )
        db.session.add(rr)
        db.session.commit()
        flash("Reorder request recorded.", "success")
        return redirect(url_for("inventory"))
    return render_template("reorder.html", material=material, suppliers=suppliers)


@app.route("/reorder/request/<int:id>/status", methods=["POST"])
def update_reorder_status(id):
    rr = ReorderRequest.query.get_or_404(id)
    status = request.form.get("status", "").strip()
    if status not in ("Ordered", "Received", "Pending"):
        flash("Invalid status.", "danger")
        return redirect(url_for("notifications"))
    rr.status = status
    db.session.commit()
    flash("Reorder status updated.", "success")
    return redirect(url_for("notifications"))


@app.route("/notifications")
def notifications():
    # Use your helper (already filters properly)
    low = build_low_stock_rows()

    return render_template(
        "notifications.html",
        low=low
    )


@app.route("/sales")
def sales():
    sales_list = (
        Sale.query.options(joinedload(
            Sale.items).joinedload(SaleItem.material))
        .order_by(Sale.date.desc())
        .all()
    )
    return render_template("sales.html", sales=sales_list)


@app.route("/sales/<int:id>")
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
def clear_sales():
    SaleItem.query.delete()
    Sale.query.delete()
    db.session.commit()
    flash("All sales records were cleared.", "success")
    return redirect(url_for("sales"))


@app.route("/sales/export")
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
def suppliers():
    if request.method == "POST":
        name = request.form["name"]
        contact = request.form["contact"]
        address = request.form["address"]
        new_supplier = Supplier(name=name, contact=contact, address=address)
        db.session.add(new_supplier)
        db.session.commit()
        flash(f"Supplier '{name}' added successfully!", "success")
        return redirect(url_for("suppliers"))

    suppliers_list = Supplier.query.all()
    return render_template("suppliers.html", suppliers=suppliers_list)


@app.route("/supplier/edit/<int:id>", methods=["GET", "POST"])
def edit_supplier(id):
    supplier = Supplier.query.get_or_404(id)
    if request.method == "POST":
        supplier.name = request.form["name"]
        supplier.contact = request.form["contact"]
        supplier.address = request.form["address"]
        db.session.commit()
        flash(f"Supplier '{supplier.name}' updated successfully!", "success")
        return redirect(url_for("suppliers"))
    return render_template("edit_supplier.html", supplier=supplier)


@app.route("/supplier/delete/<int:id>", methods=["POST"])
def delete_supplier(id):
    supplier = Supplier.query.get_or_404(id)
    db.session.delete(supplier)
    db.session.commit()
    flash(f"Supplier '{supplier.name}' deleted successfully!", "success")
    return redirect(url_for("suppliers"))


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/settings")
def settings():
    return render_template("settings.html")


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

        conn.commit()


# ------------------------------
# DATABASE INIT
# ------------------------------
with app.app_context():
    db.create_all()
    _migrate_sqlite_schema()


# ------------------------------
# RUN APP
# ------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
