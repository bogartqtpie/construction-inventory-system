import sqlite3

# Connect to SQLite database
conn = sqlite3.connect("inventory.db")
cursor = conn.cursor()

# Create Supplier table
cursor.execute("""
CREATE TABLE IF NOT EXISTS suppliers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    contact TEXT,
    address TEXT
)
""")

# Create Materials table
cursor.execute("""
CREATE TABLE IF NOT EXISTS materials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    quantity REAL NOT NULL DEFAULT 0,
    unit TEXT DEFAULT 'pcs',
    reorder_point REAL NOT NULL DEFAULT 0,
    supplier_id INTEGER,
    price_per_unit REAL DEFAULT 0,
    FOREIGN KEY(supplier_id) REFERENCES suppliers(id)
)
""")

# Create Sales table (main transaction)
cursor.execute("""
CREATE TABLE IF NOT EXISTS sales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    total REAL NOT NULL DEFAULT 0
)
""")

# Create Sale Items table (details per sale)
cursor.execute("""
CREATE TABLE IF NOT EXISTS sale_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sale_id INTEGER NOT NULL,
    material_id INTEGER NOT NULL,
    qty REAL NOT NULL,
    price REAL NOT NULL,
    FOREIGN KEY(sale_id) REFERENCES sales(id),
    FOREIGN KEY(material_id) REFERENCES materials(id)
)
""")

conn.commit()
conn.close()

print("✅ Database and tables created successfully!")
