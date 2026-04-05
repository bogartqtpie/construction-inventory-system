# models.py
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

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

    supplier_reorder_requests = db.relationship(
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
    category = db.Column(db.String(100))
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
        backref=db.backref("material", lazy=True),
        cascade="all, delete-orphan"
    )
    reorder_requests = db.relationship(
        "ReorderRequest",
        backref=db.backref("material_ref", lazy=True),
        cascade="all, delete-orphan"
    )
    variants = db.relationship(
        "MaterialVariant",
        backref=db.backref("material_ref", lazy=True),
        cascade="all, delete-orphan"
    )

    def total_quantity(self):
        if self.variants:
            return sum(v.quantity for v in self.variants)
        return self.quantity

    def status(self):
        qty = self.total_quantity()
        if qty == 0:
            return "OUT"
        if qty <= self.reorder_point:
            return "LOW"
        return "OK"

    def recommended_reorder_qty(self, forecast_rain_factor=1.0):
        base_qty = max(self.reorder_point - self.total_quantity(), 0)
        return round(base_qty * forecast_rain_factor, 2)

    def __repr__(self):
        return f"<Material {self.name}>"

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
    dismissed = db.Column(db.Boolean, default=False)  # For dismiss button

    def mark_received(self):
        if self.material_ref:
            self.material_ref.quantity += self.requested_qty
        self.status = "Received"
        db.session.commit()

    def __repr__(self):
        name = getattr(self.material_ref, "name", "unknown")
        return f"<ReorderRequest Material={name}, Status={self.status}, Dismissed={self.dismissed}>"

# ---------------- MaterialVariant ----------------


class MaterialVariant(db.Model):
    __tablename__ = "material_variant"
    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True)
    material_id = db.Column(db.Integer, db.ForeignKey(
        "material.id"), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Float, default=0)
    unit = db.Column(db.String(50), default="pcs")
    price = db.Column(db.Float, default=0.0)

    def __repr__(self):
        return f"<MaterialVariant {self.name} of Material ID={self.material_id}>"

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

# ---------------- Sale ----------------


class Sale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    total = db.Column(db.Float, default=0)
    type = db.Column(db.String(20), default="sale")

    items = db.relationship(
        "SaleItem",
        backref=db.backref("sale_ref", lazy=True),
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Sale ID={self.id}, Total={self.total}, Type={self.type}>"

# ---------------- SaleItem ----------------


class SaleItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey("sale.id"), nullable=False)
    material_id = db.Column(db.Integer, db.ForeignKey(
        "material.id"), nullable=False)
    qty = db.Column(db.Float, nullable=False)
    price = db.Column(db.Float, nullable=False, default=0)

    def __repr__(self):
        name = getattr(self.material, "name", "unknown")
        return f"<SaleItem Material={name}, Qty={self.qty}, Price={self.price}>"
