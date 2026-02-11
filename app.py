from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file
from models import db, Material, Supplier, UsageLog, Sale, SaleItem
from utils import get_low_stock, predict_depletion_days
from flask_migrate import Migrate
from datetime import datetime
import csv
import io


def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///inventory.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
    migrate = Migrate(app, db)

    # ---------------- INDEX ----------------
    @app.route('/')
    def index():
        materials = Material.query.order_by(Material.name).all()
        return render_template('index.html', materials=materials, low_count=len(get_low_stock()))

    # ---------------- INVENTORY ----------------
    @app.route('/inventory')
    def inventory():
        materials = Material.query.order_by(Material.name).all()
        return render_template('inventory.html', materials=materials, low_count=len(get_low_stock()))

    # ---------------- ADD MATERIAL ----------------
    @app.route('/materials/add', methods=['GET', 'POST'])
    def add_material():
        suppliers = Supplier.query.order_by(Supplier.name).all()
        if request.method == 'POST':
            price_value = request.form.get(
                'price') or request.form.get('price_per_unit') or 0
            new_material = Material(
                name=request.form['name'],
                quantity=float(request.form.get('quantity', 0)),
                unit=request.form.get('unit', 'pcs'),
                reorder_point=float(request.form.get('reorder_point', 0)),
                supplier_id=request.form.get('supplier_id') or None,
                price_per_unit=float(price_value) if price_value else 0.0
            )
            db.session.add(new_material)
            db.session.commit()
            return redirect(url_for('inventory'))
        return render_template('add_edit_material.html', suppliers=suppliers, material=None, low_count=len(get_low_stock()))

    # ---------------- EDIT MATERIAL ----------------
    @app.route('/materials/<int:id>/edit', methods=['GET', 'POST'])
    def edit_material(id):
        material = Material.query.get_or_404(id)
        suppliers = Supplier.query.order_by(Supplier.name).all()

        if request.method == 'POST':
            material.name = request.form['name']
            material.quantity = float(request.form.get('quantity', 0))
            material.unit = request.form.get('unit', material.unit)
            material.reorder_point = float(
                request.form.get('reorder_point', 0))
            material.supplier_id = request.form.get('supplier_id') or None
            price_value = request.form.get(
                'price') or request.form.get('price_per_unit')
            material.price_per_unit = float(
                price_value) if price_value else 0.0

            db.session.commit()
            return redirect(url_for('inventory'))

        return render_template('add_edit_material.html', material=material, suppliers=suppliers, low_count=len(get_low_stock()))

    # ---------------- DELETE MATERIAL ----------------
    @app.route('/materials/<int:id>/delete', methods=['POST'])
    def delete_material(id):
        material = Material.query.get_or_404(id)
        db.session.delete(material)
        db.session.commit()
        return redirect(url_for('inventory'))

    # ---------------- REORDER MATERIAL ----------------
    @app.route('/materials/<int:material_id>/reorder', methods=['GET', 'POST'])
    def reorder(material_id):
        material = Material.query.get_or_404(material_id)
        suppliers = Supplier.query.all()

        if request.method == 'POST':
            reorder_qty = float(request.form.get('reorder_qty', 0))
            if reorder_qty <= 0:
                return render_template('reorder.html', material=material, suppliers=suppliers, error="Please enter a valid quantity.", low_count=len(get_low_stock()))

            material.quantity += reorder_qty
            db.session.commit()
            return redirect(url_for('inventory'))

        return render_template('reorder.html', material=material, suppliers=suppliers, low_count=len(get_low_stock()))

    # ---------------- SUPPLIERS ----------------
    @app.route('/suppliers', methods=['GET', 'POST'])
    def suppliers():
        if request.method == 'POST':
            s = Supplier(name=request.form['name'], contact=request.form.get(
                'contact'), address=request.form.get('address'))
            db.session.add(s)
            db.session.commit()
            return redirect(url_for('suppliers'))
        suppliers = Supplier.query.order_by(Supplier.name).all()
        return render_template('suppliers.html', suppliers=suppliers, low_count=len(get_low_stock()))

    @app.route('/suppliers/<int:id>/edit', methods=['GET', 'POST'])
    def edit_supplier(id):
        supplier = Supplier.query.get_or_404(id)
        if request.method == 'POST':
            supplier.name = request.form['name']
            supplier.contact = request.form.get('contact')
            supplier.address = request.form.get('address')
            db.session.commit()
            return redirect(url_for('suppliers'))
        return render_template('edit_supplier.html', supplier=supplier, low_count=len(get_low_stock()))

    @app.route('/suppliers/<int:id>/delete', methods=['POST'])
    def delete_supplier(id):
        s = Supplier.query.get_or_404(id)
        db.session.delete(s)
        db.session.commit()
        return redirect(url_for('suppliers'))

    # ---------------- CHECKOUT / SALES ----------------
    @app.route("/checkout", methods=["POST"])
    def checkout():
        data = request.get_json(silent=True) or {}
        cart = data.get("cart", [])

        if not cart:
            return jsonify({"success": False, "message": "Cart is empty."})

        sale = Sale(date=datetime.utcnow())
        db.session.add(sale)

        try:
            total_amount = 0.0

            for item in cart:
                material_id = int(item.get("id"))
                qty = float(item.get("qty", item.get("quantity", 0)))
                price = float(item.get("price", item.get("price_per_unit", 0)))

                material = db.session.get(Material, material_id)
                if not material:
                    return jsonify({"success": False, "message": f"Material with ID {material_id} not found."})

                if material.quantity < qty:
                    return jsonify({"success": False, "message": f"Not enough stock for {material.name}. Available: {material.quantity}"})

                material.quantity -= qty
                if material.quantity < 0:
                    material.quantity = 0

                sale_item = SaleItem(
                    sale_id=sale.id, material_id=material.id, qty=qty, price=price)
                db.session.add(sale_item)
                total_amount += qty * price

            sale.total = total_amount
            db.session.commit()

            updated_inventory = [
                {"id": m.id, "name": m.name, "quantity": m.quantity,
                    "unit": m.unit, "reorder_point": m.reorder_point}
                for m in Material.query.order_by(Material.name).all()
            ]
            return jsonify({"success": True, "updated_inventory": updated_inventory})

        except Exception as e:
            db.session.rollback()
            return jsonify({"success": False, "message": str(e)})

    # ---------------- SALES ----------------
    @app.route('/sales')
    def sales():
        sales = Sale.query.order_by(Sale.date.desc()).all()
        return render_template('sales.html', sales=sales, low_count=len(get_low_stock()))

    @app.route('/sale/<int:id>')
    def sale_view(id):
        sale = Sale.query.get_or_404(id)
        return render_template('sale_view.html', sale=sale, low_count=len(get_low_stock()))

    @app.route('/sales/export')
    def sales_export():
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Sale ID', 'Date', 'Total'])
        for s in Sale.query.order_by(Sale.date.desc()).all():
            writer.writerow(
                [s.id, s.date.strftime("%Y-%m-%d %H:%M:%S"), s.total])
        output.seek(0)
        return send_file(io.BytesIO(output.getvalue().encode('utf-8')), mimetype='text/csv', as_attachment=True, download_name='sales_export.csv')

    # ---------------- NOTIFICATIONS ----------------
    @app.route('/notifications')
    def notifications():
        low = [m for m in Material.query.order_by(
            Material.name).all() if m.quantity <= m.reorder_point]
        low_with_prediction = []
        for m in low:
            days = predict_depletion_days(m)
            low_with_prediction.append(
                {"id": m.id, "name": m.name, "qty": m.quantity, "pred_days": days})
        return render_template('notifications.html', low=low_with_prediction, low_count=len(low_with_prediction))

    # ---------------- SETTINGS & ABOUT ----------------
    @app.route('/settings')
    def settings():
        return render_template('settings.html', low_count=len(get_low_stock()))

    @app.route('/about')
    def about():
        return render_template('about.html', low_count=len(get_low_stock()))

    return app


# ✅ Expose the app instance for Render
app = create_app()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
