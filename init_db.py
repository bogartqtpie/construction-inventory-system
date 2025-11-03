from app import create_app
from models import db, Material, Supplier, UsageLog, Sale, SaleItem
from datetime import datetime, timedelta
import random

app = create_app()
app.app_context().push()

# Create all tables
db.create_all()

# --- Add Default Supplier ---
if not Supplier.query.first():
    s = Supplier(name="Default Supplier",
                 contact="09171234567", address="Barangay 1")
    db.session.add(s)
    db.session.commit()
else:
    s = Supplier.query.first()

# --- Add Sample Materials ---
if not Material.query.first():
    materials = [
        {"name": "Cement (40kg bag)", "unit": "bag",
         "quantity": 120, "reorder_point": 30},
        {"name": "Gravel (m3)", "unit": "m3", "quantity": 60,
         "reorder_point": 15},
        {"name": "Sand (m3)", "unit": "m3", "quantity": 80,
         "reorder_point": 20},
        {"name": "Rebar 12mm", "unit": "pcs", "quantity": 200, "reorder_point": 50},
        {"name": "Hollow Block 6\"", "unit": "pcs",
            "quantity": 500, "reorder_point": 100},
        {"name": "Plywood 4x8", "unit": "sheet",
            "quantity": 40, "reorder_point": 10},
        {"name": "Paint 5L", "unit": "can", "quantity": 25, "reorder_point": 5},
    ]

    for m in materials:
        mat = Material(
            name=m['name'],
            unit=m['unit'],
            quantity=m['quantity'],
            reorder_point=m['reorder_point'],
            supplier_id=s.id
        )
        db.session.add(mat)
    db.session.commit()

# --- Add Usage Logs (Past 15 Days) ---
if not UsageLog.query.first():
    for mat in Material.query.limit(4).all():
        for i in range(1, 16):
            used = random.randint(1, 10)
            log_date = datetime.utcnow() - timedelta(days=16 - i)
            log = UsageLog(material_id=mat.id,
                           used_quantity=used, date=log_date)
            db.session.add(log)
    db.session.commit()


print("✅ Database initialized with sample data successfully!")
