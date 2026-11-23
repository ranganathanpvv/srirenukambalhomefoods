import os
from dotenv import load_dotenv

import certifi
os.environ.setdefault("SSL_CERT_FILE", certifi.where())
os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())

import sqlite3
import libsql
from pathlib import Path
from contextlib import contextmanager
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("DATABASE_PATH", BASE_DIR / "data" / "renukambal.db"))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

TURSO_URL = os.environ.get("TURSO_DATABASE_URL")
TURSO_TOKEN = os.environ.get("TURSO_AUTH_TOKEN")


class DictCursor:
    """Wraps libsql cursor so fetchone() and fetchall() return dicts just like sqlite3.Row."""
    def __init__(self, cursor):
        self._cursor = cursor

    @property
    def lastrowid(self):
        return self._cursor.lastrowid

    @property
    def rowcount(self):
        return self._cursor.rowcount

    def _to_dict(self, row):
        if row is None or isinstance(row, dict):
            return row
        cols = [d[0] for d in self._cursor.description]
        return dict(zip(cols, row))

    def fetchone(self):
        return self._to_dict(self._cursor.fetchone())

    def fetchall(self):
        return [self._to_dict(r) for r in self._cursor.fetchall()]


class LibsqlWrapper:
    """Makes libsql connection behave identically to your existing sqlite3 setup."""
    def __init__(self, conn, is_turso=False):
        self._conn = conn
        self._is_turso = is_turso

    def execute(self, sql, params=()):
        return DictCursor(self._conn.execute(sql, params))

    def executemany(self, sql, seq_of_params):
        return DictCursor(self._conn.executemany(sql, seq_of_params))

    def executescript(self, script):
        return self._conn.executescript(script)

    def commit(self):
        self._conn.commit()
        if self._is_turso:
            self._conn.sync()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()


@contextmanager
def get_db():
    if TURSO_URL and TURSO_TOKEN:
        raw_conn = libsql.connect(
            str(DB_PATH),
            sync_url=TURSO_URL,
            auth_token=TURSO_TOKEN
        )
        raw_conn.sync()
        conn = LibsqlWrapper(raw_conn, is_turso=True)
    else:
        raw_conn = sqlite3.connect(DB_PATH)
        raw_conn.row_factory = sqlite3.Row
        conn = LibsqlWrapper(raw_conn, is_turso=False)

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


def delete_order(order_id):
    with get_db() as conn:
        cur = conn.execute("DELETE FROM orders WHERE id=?", (order_id,))
        return cur.rowcount > 0
