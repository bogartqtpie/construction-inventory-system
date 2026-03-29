from app import create_app
from models import db, Material, Supplier, UsageLog
from datetime import datetime, timedelta
import random

app = create_app()
with app.app_context():
    db.create_all()

    # --- Add Default Supplier ---
    if not Supplier.query.first():
        s = Supplier(name="Default Supplier",
                     contact="09171234567", address="Barangay 1")
        db.session.add(s)
        db.session.commit()
    else:
        s = Supplier.query.first()

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
