import json
import os
import sqlite3
from pathlib import Path
from contextlib import contextmanager
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("DATABASE_PATH", BASE_DIR / "data" / "renukambal.db"))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with get_db() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_number TEXT UNIQUE NOT NULL,
            customer_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            address TEXT NOT NULL,
            notes TEXT,
            total REAL,
            status TEXT NOT NULL DEFAULT 'New',
            tentative_delivery_date TEXT,
            admin_remarks TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
            product_id TEXT NOT NULL,
            product_name TEXT NOT NULL,
            variant TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price REAL
        );
        CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at);
        CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
        CREATE INDEX IF NOT EXISTS idx_orders_phone ON orders(phone);
        """)


def create_order(name, phone, address, notes, items, total):
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    with get_db() as conn:
        cur = conn.execute(
            """INSERT INTO orders
            (order_number, customer_name, phone, address, notes, total, status, created_at, updated_at)
            VALUES ('PENDING', ?, ?, ?, ?, ?, 'New', ?, ?)""",
            (name, phone, address, notes, total, now, now)
        )
        order_id = cur.lastrowid
        order_number = f"RHF-{datetime.now().strftime('%y%m')}-{order_id:05d}"
        conn.execute("UPDATE orders SET order_number=? WHERE id=?", (order_number, order_id))
        conn.executemany(
            """INSERT INTO order_items
            (order_id, product_id, product_name, variant, quantity, unit_price)
            VALUES (?, ?, ?, ?, ?, ?)""",
            [(order_id, i["product_id"], i["product_name"], i["variant"], i["quantity"], i["unit_price"]) for i in items]
        )
        return order_id


def _order_dict(row, items):
    result = dict(row)
    result["items"] = [dict(x) for x in items]
    return result


def get_order(order_id):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
        if not row:
            return None
        items = conn.execute("SELECT * FROM order_items WHERE order_id=? ORDER BY id", (order_id,)).fetchall()
        return _order_dict(row, items)


def list_orders(status="", search=""):
    sql = "SELECT * FROM orders WHERE 1=1"
    params = []
    if status:
        sql += " AND status=?"
        params.append(status)
    if search:
        term = f"%{search}%"
        sql += " AND (order_number LIKE ? OR customer_name LIKE ? OR phone LIKE ?)"
        params.extend([term, term, term])
    sql += " ORDER BY id DESC LIMIT 300"
    with get_db() as conn:
        rows = conn.execute(sql, params).fetchall()
        output = []
        for row in rows:
            items = conn.execute("SELECT * FROM order_items WHERE order_id=? ORDER BY id", (row["id"],)).fetchall()
            output.append(_order_dict(row, items))
        return output


def update_order(order_id, status, delivery_date, remarks):
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    with get_db() as conn:
        conn.execute(
            """UPDATE orders SET status=?, tentative_delivery_date=?, admin_remarks=?, updated_at=?
            WHERE id=?""",
            (status, delivery_date, remarks, now, order_id)
        )
