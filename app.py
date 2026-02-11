from flask import Flask, render_template, request, jsonify, redirect, url_for


def create_app():
    app = Flask(__name__)

    # Sample materials data (including old fields)
    materials = [
        {
            "id": 1,
            "name": 'Concrete Hollow Blocks (4")',
            "quantity": 585,
            "unit": "pcs",
            "reorder_point": 500,
            "supplier": "123 Construction Corp"
        },
        {
            "id": 2,
            "name": 'Concrete Hollow Blocks (5")',
            "quantity": 5299,
            "unit": "pcs",
            "reorder_point": 500,
            "supplier": "123 Construction Corp"
        },
    ]

    # --- Routes ---
    @app.route("/")
    @app.route("/home")
    def home():
        return render_template("checkout.html", materials=materials)

    @app.route("/inventory")
    def inventory():
        # Compute status for each material
        for m in materials:
            m["status"] = "OK" if m["quantity"] > m["reorder_point"] else "LOW"
        return render_template("inventory.html", materials=materials)

    @app.route("/add_material", methods=["GET", "POST"])
    def add_material():
        if request.method == "POST":
            name = request.form.get("name")
            quantity = float(request.form.get("quantity"))
            unit = request.form.get("unit")
            materials.append({
                "id": len(materials) + 1,
                "name": name,
                "quantity": quantity,
                "unit": unit,
                "reorder_point": 0,
                "supplier": "Default Supplier",
                "status": "OK"
            })
            return redirect(url_for("inventory"))
        return render_template("add_material.html")

    @app.route("/sales")
    def sales():
        return "<h1>Sales Page</h1>"

    @app.route("/suppliers")
    def suppliers():
        return "<h1>Suppliers Page</h1>"

    @app.route("/settings")
    def settings():
        return "<h1>Settings Page</h1>"

    @app.route("/about")
    def about():
        return "<h1>About Page</h1>"

    @app.route("/notifications")
    def notifications():
        return "<h1>Notifications Page</h1>"

    return app


if __name__ == "__main__":
    create_app().run(debug=True)
