# app.py
from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file
from models import db, Material, Supplier, UsageLog, Sale, SaleItem, ReorderRequest
from utils import get_low_stock, predict_depletion_days
from flask_migrate import Migrate
from datetime import datetime
import csv
import io
import os


def create_app():
    app = Flask(__name__)

    # ---------------- CONFIG ----------------
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///inventory.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
    Migrate(app, db)

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

    # ---------------- ADD / EDIT / DELETE MATERIAL ----------------
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

    @app.route('/materials/<int:id>/delete', methods=['POST'])
    def delete_material(id):
        material = Material.query.get_or_404(id)
        db.session.delete(material)
        db.session.commit()
        return redirect(url_for('inventory'))

    # ---------------- ORDER MATERIAL ----------------
    @app.route('/materials/<int:material_id>/order', methods=['GET', 'POST'])
    def order_material(material_id):
        material = Material.query.get_or_404(material_id)
        suppliers = Supplier.query.order_by(Supplier.name).all()
        if request.method == 'POST':
            reorder_qty = float(request.form.get('reorder_qty', 0))
            supplier_id = request.form.get('supplier_id') or None
            if reorder_qty <= 0:
                return render_template('order_material.html', material=material, suppliers=suppliers,
                                       error="Please enter a valid quantity.", low_count=len(get_low_stock()))
            reorder_request = ReorderRequest(
                material_id=material.id,
                supplier_id=supplier_id,
                requested_qty=reorder_qty,
                status="Pending"
            )
            db.session.add(reorder_request)
            db.session.commit()
            return redirect(url_for('notifications'))
        return render_template('order_material.html', material=material, suppliers=suppliers, low_count=len(get_low_stock()))

    @app.route('/reorder/<int:id>/update', methods=['POST'])
    def update_reorder_status(id):
        reorder = ReorderRequest.query.get_or_404(id)
        new_status = request.form.get('status')
        if new_status in ['Pending', 'Ordered', 'Received']:
            reorder.status = new_status
            db.session.commit()
        if reorder.status == 'Received':
            material = Material.query.get(reorder.material_id)
            if material:
                material.quantity += reorder.requested_qty
                db.session.commit()
        return redirect(url_for('notifications'))

    # ---------------- SUPPLIERS ----------------
    @app.route('/suppliers', methods=['GET', 'POST'])
    def suppliers():
        if request.method == 'POST':
            s = Supplier(
                name=request.form['name'],
                contact=request.form.get('contact'),
                address=request.form.get('address')
            )
            db.session.add(s)
            db.session.commit()
            return redirect(url_for('suppliers'))
        suppliers_list = Supplier.query.order_by(Supplier.name).all()
        return render_template('suppliers.html', suppliers=suppliers_list, low_count=len(get_low_stock()))

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

    # ---------------- SALES ----------------
    @app.route('/sales')
    def sales():
        sales_list = Sale.query.order_by(Sale.id.desc()).all()
        return render_template('sales.html', sales=sales_list, low_count=len(get_low_stock()))

    @app.route('/sales/<int:id>')
    def sale_view(id):
        sale = Sale.query.get_or_404(id)
        return render_template('sale_view.html', sale=sale, low_count=len(get_low_stock()))

    @app.route('/sales/export')
    def sales_export():
        sales_list = Sale.query.order_by(Sale.date.desc()).all()
        output = io.StringIO()
        writer = csv.writer(output, delimiter=',',
                            quotechar='"', quoting=csv.QUOTE_MINIMAL)
        writer.writerow(['Sale ID', 'Date', 'Total (₱)', 'Items'])
        for sale in sales_list:
            items = ', '.join(
                [f"{i.material.name} × {i.qty}" for i in sale.items])
            writer.writerow([sale.id, sale.date.strftime(
                "%Y-%m-%d %H:%M:%S"), f"₱{sale.total:.2f}", items])

        data = output.getvalue().encode('utf-16')  # UTF-16 for Excel Windows

        return send_file(
            io.BytesIO(data),
            mimetype='text/csv',
            as_attachment=True,
            download_name='sales_export.csv'
        )

    # ---------------- CHECKOUT ----------------
    @app.route('/checkout', methods=['POST'])
    def checkout():
        try:
            data = request.get_json(force=True, silent=True)
            if not data:
                return jsonify({'error': 'Invalid or missing JSON data'}), 400

            items = data.get('items') or data.get('cart') or []
            if not isinstance(items, list) or len(items) == 0:
                return jsonify({'error': 'No items provided'}), 400

            sale = Sale(date=datetime.utcnow(), total=0)
            db.session.add(sale)
            db.session.flush()

            low_stock = []
            for item in items:
                material_id = int(item.get('material_id') or item.get('id'))
                qty = float(item.get('qty', 0))

                material = Material.query.get(material_id)
                if not material:
                    return jsonify({'error': f'Material ID {material_id} not found'}), 404
                if material.quantity < qty:
                    return jsonify({'error': f'Not enough stock for {material.name}'}), 400

                price = float(material.price_per_unit or 0.0)
                subtotal = price * qty
                material.quantity -= qty

                sale_item = SaleItem(
                    sale_id=sale.id,
                    material_id=material.id,
                    qty=qty,
                    price=price
                )
                db.session.add(sale_item)
                db.session.add(UsageLog(material_id=material.id,
                               used_quantity=qty, date=datetime.utcnow()))

                if material.quantity <= material.reorder_point:
                    low_stock.append(
                        {'name': material.name, 'qty': material.quantity})

                sale.total = (sale.total or 0) + subtotal

            db.session.commit()
            return jsonify({'success': True, 'message': 'Checkout successful', 'sale_id': sale.id, 'low': low_stock}), 200

        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500

    # ---------------- NOTIFICATIONS ----------------
    @app.route('/notifications')
    def notifications():
        low = [m for m in Material.query.order_by(
            Material.name).all() if m.quantity <= m.reorder_point]
        low_with_prediction = []
        for m in low:
            days = predict_depletion_days(m)
            reorder_requests = ReorderRequest.query.filter_by(
                material_id=m.id).order_by(ReorderRequest.id.desc()).all()
            low_with_prediction.append({
                "id": m.id,
                "name": m.name,
                "qty": m.quantity,
                "unit": m.unit,
                "pred_days": days,
                "reorder_requests": reorder_requests
            })
        return render_template('notifications.html', low=low_with_prediction, low_count=len(low_with_prediction))

    # ---------------- SETTINGS & ABOUT ----------------
    @app.route('/settings')
    def settings():
        return render_template('settings.html', low_count=len(get_low_stock()))

    @app.route('/about')
    def about():
        return render_template('about.html', low_count=len(get_low_stock()))

    # ---------------- ADMIN ----------------
    @app.route('/sales/clear', methods=['POST'])
    def clear_sales():
        SaleItem.query.delete()
        Sale.query.delete()
        db.session.commit()
        return redirect(url_for('sales'))

    @app.route('/reset/full', methods=['POST'])
    def full_reset():
        SaleItem.query.delete()
        Sale.query.delete()
        UsageLog.query.delete()
        ReorderRequest.query.delete()
        Material.query.delete()
        Supplier.query.delete()
        db.session.commit()
        return redirect(url_for('index'))

    return app
