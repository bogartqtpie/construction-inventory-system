from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# 1️⃣ Initialize SQLAlchemy
db = SQLAlchemy()

# ---------------- Supplier Model ----------------


class Supplier(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    contact = db.Column(db.String(150))
    address = db.Column(db.String(250))

    materials = db.relationship(
        "Material",
        backref=db.backref("supplier", lazy=True),
        cascade="all, delete-orphan"
    )

    reorder_requests = db.relationship(
        "ReorderRequest",
        backref=db.backref("supplier_ref", lazy=True),
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Supplier {self.name}>"

# ---------------- Material Model ----------------


class Material(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, unique=True)
    unit = db.Column(db.String(50), default="pcs")
    quantity = db.Column(db.Float, default=0)
    reorder_point = db.Column(db.Float, default=0)
    price_per_unit = db.Column(db.Float, default=0.0)
    price = db.Column(db.Float, default=0)
    subtotal = db.Column(db.Float)

    supplier_id = db.Column(
        db.Integer, db.ForeignKey("supplier.id"), nullable=True)

    usage_logs = db.relationship(
        "UsageLog",
        backref=db.backref("material_ref", lazy=True),
        cascade="all, delete-orphan"
    )

    sale_items = db.relationship(
        "SaleItem",
        # This fixes your Jinja error
        backref=db.backref("material", lazy=True),
        cascade="all, delete-orphan"
    )

    reorder_requests = db.relationship(
        "ReorderRequest",
        backref=db.backref("material_ref", lazy=True),
        cascade="all, delete-orphan"
    )

    def status(self):
        return "LOW" if self.quantity <= self.reorder_point else "OK"

    def __repr__(self):
        return f"<Material {self.name}>"

# ---------------- UsageLog ----------------


class UsageLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    material_id = db.Column(db.Integer, db.ForeignKey(
        "material.id"), nullable=False)
    used_quantity = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        name = getattr(self.material_ref, "name", "unknown")
        return f"<UsageLog Material={name}, Used={self.used_quantity}>"

# ---------------- Sale and SaleItem ----------------


class Sale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    total = db.Column(db.Float, default=0)

    items = db.relationship(
        "SaleItem",
        backref=db.backref("sale_ref", lazy=True),
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Sale ID={self.id}, Total={self.total}>"


class SaleItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey("sale.id"), nullable=False)
    material_id = db.Column(db.Integer, db.ForeignKey(
        "material.id"), nullable=False)
    qty = db.Column(db.Float, nullable=False)
    price = db.Column(db.Float, nullable=False, default=0)

    def __repr__(self):
        # uses correct backref
        name = getattr(self.material, "name", "unknown")
        return f"<SaleItem Material={name}, Qty={self.qty}, Price={self.price}>"

# ---------------- ReorderRequest ----------------


class ReorderRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    material_id = db.Column(db.Integer, db.ForeignKey(
        "material.id"), nullable=False)
    supplier_id = db.Column(
        db.Integer, db.ForeignKey("supplier.id"), nullable=True)
    requested_qty = db.Column(db.Float, nullable=False)
    request_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(50), default="Pending")

    def mark_received(self):
        self.status = "Received"
        db.session.commit()

    def __repr__(self):
        name = getattr(self.material_ref, "name", "unknown")
        return f"<ReorderRequest Material={name}, Status={self.status}>"
