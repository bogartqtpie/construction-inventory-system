from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

# -------------------------
# Supplier Model
# -------------------------


class Supplier(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    contact = db.Column(db.String(150))
    address = db.Column(db.String(250))

    def __repr__(self):
        return f"<Supplier {self.name}>"


# -------------------------
# Material Model
# -------------------------
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
    supplier = db.relationship("Supplier", backref="materials")

    def status(self):
        return "LOW" if self.quantity <= self.reorder_point else "OK"

    def __repr__(self):
        return f"<Material {self.name}>"


# -------------------------
# Usage Log
# -------------------------
class UsageLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    material_id = db.Column(db.Integer, db.ForeignKey(
        "material.id"), nullable=False)
    used_quantity = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    material = db.relationship("Material", backref="usage_logs")


# -------------------------
# Sales Models
# -------------------------
class Sale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    total = db.Column(db.Float, default=0)


class SaleItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey("sale.id"))
    material_id = db.Column(db.Integer, db.ForeignKey("material.id"))
    qty = db.Column(db.Float, nullable=False)
    price = db.Column(db.Float, nullable=False, default=0)
    sale = db.relationship("Sale", backref="items")
    material = db.relationship("Material")


# -------------------------
# Reorder Request Model (New)
# -------------------------
class ReorderRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    material_id = db.Column(db.Integer, db.ForeignKey(
        "material.id"), nullable=False)
    supplier_id = db.Column(
        db.Integer, db.ForeignKey("supplier.id"), nullable=True)
    requested_qty = db.Column(db.Float, nullable=False)
    request_date = db.Column(db.DateTime, default=datetime.utcnow)
    # Pending, Ordered, Received
    status = db.Column(db.String(50), default="Pending")

    # Relationships
    material = db.relationship("Material", backref="reorder_requests")
    supplier = db.relationship("Supplier", backref="reorder_requests")

    def __repr__(self):
        return f"<ReorderRequest Material={self.material.name}, Status={self.status}>"
