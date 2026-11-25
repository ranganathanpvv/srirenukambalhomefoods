import json
import os
import sqlite3
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

TURSO_URL = os.environ.get("TURSO_DATABASE_URL", "").strip()
TURSO_TOKEN = os.environ.get("TURSO_AUTH_TOKEN", "").strip()
SQLITE_PATH = os.environ.get("SQLITE_DB_PATH", "app.db").strip()

ORDER_CLAUSES = [
    "Minimum order quantity applies per product as indicated on the item.",
    "Listed prices include a base delivery charge; however, additional delivery charges may apply in certain cases (such as higher weight slabs, multi-item orders, or outstation/remote locations) and will be confirmed on WhatsApp.",
    "Products are prepared in small batches or on request, subject to availability; final confirmation of availability, any additional delivery charges, and tentative dispatch/delivery details will be shared on WhatsApp.",
]

PRODUCTS = [
    {
        "id": "idli-podi",
        "name": "Idli Podi",
        "description": "Homemade podi, available with or without garlic. Base delivery included.",
        "card_note": "2 × 250g gets 500g pack price · ~14% off 1kg",
        "category": "Podi",
        "image": "/static/images/idli-podi.jpg",
        "min_qty": 1,
        "variants": [
            {"name": "250g", "price": 193},
            {"name": "500g", "price": 367},
            {"name": "1kg", "price": 654},
        ],
        "attributes": [
            {
                "key": "garlic",
                "label": "Garlic preference",
                "options": [
                    {"value": "With Garlic", "price_delta": 0.0},
                    {"value": "Without Garlic", "price_delta": 0.0},
                ],
            }
        ],
    },
    {
        "id": "sambar-podi",
        "name": "Sambar Podi",
        "description": "Traditional homemade sambar podi. Base delivery included.",
        "card_note": "2 × 250g gets 500g pack price · ~14% off 1kg",
        "category": "Spice Powders",
        "image": "/static/images/sambar-powder.jpg",
        "min_qty": 1,
        "variants": [
            {"name": "250g", "price": 213},
            {"name": "500g", "price": 404},
            {"name": "1kg", "price": 723},
        ],
        "attributes": [],
    },
    {
        "id": "rasam-podi",
        "name": "Rasam podi",
        "description": "Aromatic homemade rasam podi. Base delivery included.",
        "card_note": "2 × 250g gets 500g pack price · ~14% off 1kg",
        "category": "Spice Powders",
        "image": "/static/images/rasam-powder.jpg",
        "min_qty": 1,
        "variants": [
            {"name": "250g", "price": 234},
            {"name": "500g", "price": 443},
            {"name": "1kg", "price": 794},
        ],
        "attributes": [],
    },
    {
        "id": "paruppu-podi",
        "name": "Paruppu Podi",
        "description": "Traditional homemade lentil podi. Base delivery included.",
        "card_note": "2 × 250g gets 500g pack price · ~14% off 1kg",
        "category": "Podi",
        "image": "/static/images/paruppu-podi.jpg",
        "min_qty": 1,
        "variants": [
            {"name": "250g", "price": 214},
            {"name": "500g", "price": 407},
            {"name": "1kg", "price": 727},
        ],
        "attributes": [
            {
                "key": "garlic",
                "label": "Garlic preference",
                "options": [
                    {"value": "With Garlic", "price_delta": 0.0},
                    {"value": "Without Garlic", "price_delta": 0.0},
                ],
            }
        ],
    },
    {
        "id": "lemon-pickle",
        "name": "Lemon Pickle",
        "description": "(Seasonal) Homemade lemon pickle, prepared on request. Base delivery included.",
        "card_note": "Prepared on request · 2 × 250g gets 500g price",
        "category": "Pickles",
        "image": "/static/images/lemon-pickle.jpg",
        "min_qty": 1,
        "variants": [
            {"name": "250g", "price": 223},
            {"name": "500g", "price": 424},
            {"name": "1kg", "price": 757},
        ],
        "attributes": [],
    },
    {
        "id": "shikakai-podi",
        "name": "Shikakai Podi",
        "description": "Traditional shikakai powder for hair care. Base delivery included.",
        "card_note": "2 × 250g gets 500g pack price · ~14% off 1kg",
        "category": "Personal Care",
        "image": "/static/images/shikakai-powder.jpg",
        "min_qty": 1,
        "variants": [
            {"name": "250g", "price": 224},
            {"name": "500g", "price": 427},
            {"name": "1kg", "price": 757},
        ],
        "attributes": [],
    },
    {
        "id": "karuvepilai-podi",
        "name": "Karuvepilai Podi",
        "description": "Homemade karuvepilai podi, prepared on request. Base delivery included.",
        "card_note": "2 × 250g gets 500g pack price · ~14% off 1kg",
        "category": "Personal Care",
        "image": "/static/images/karuvepilai-podi.jpg",
        "min_qty": 1,
        "variants": [
            {"name": "250g", "price": 187},
            {"name": "500g", "price": 355},
            {"name": "1kg", "price": 710},
        ],
        "attributes": [],
    },
    {
        "id": "arisi-upma-readytomix",
        "name": "Arisi Upma Ready TO Mix",
        "description": "Homemade arisi upma mix, prepared on request. 250g can server 2-3 pax. Base delivery included.",
        "card_note": "2 × 250g gets 500g pack price · ~14% off 1kg",
        "category": "Personal Care",
        "image": "/static/images/arisi-upma-readytomix.jpg",
        "min_qty": 1,
        "variants": [
            {"name": "250g", "price": 115},
            {"name": "500g", "price": 217},
            {"name": "1kg", "price": 354},
        ],
        "attributes": [],
    },
    {
        "id": "puzhungal-kanji-mix",
        "name": "Puzhungal Arisi Kanji mix",
        "description": "Homemade Puzhungal Arisi Kanji mix, prepared on request. Base delivery included.",
        "card_note": "2 × 250g gets 500g pack price · ~14% off 1kg",
        "category": "Personal Care",
        "image": "/static/images/puzhungal-kanji-mix.jpg",
        "min_qty": 1,
        "variants": [
            {"name": "250g", "price": 117},
            {"name": "500g", "price": 213},
            {"name": "1kg", "price": 353},
        ],
        "attributes": [],
    },
]


def _turso_http_url() -> str:
    url = TURSO_URL.replace("libsql://", "https://").rstrip("/")
    return f"{url}/v2/pipeline"


def _encode_arg(val):
    if val is None:
        return {"type": "null"}
    if isinstance(val, bool):
        return {"type": "integer", "value": str(int(val))}
    if isinstance(val, int):
        return {"type": "integer", "value": str(val)}
    if isinstance(val, float):
        return {"type": "float", "value": val}
    return {"type": "text", "value": str(val)}


def _decode_val(cell: dict):
    cell_type = cell.get("type")
    if cell_type == "null":
        return None
    if cell_type == "integer":
        return int(cell.get("value", 0))
    if cell_type == "float":
        return float(cell.get("value", 0.0))
    return cell.get("value")


def _query_db(sql: str, params: list | None = None) -> list[dict]:
    args = params or []

    if TURSO_URL and TURSO_TOKEN:
        stmt = {"sql": sql}
        if args:
            stmt["positional_args"] = [_encode_arg(a) for a in args]

        resp = requests.post(
            _turso_http_url(),
            headers={
                "Authorization": f"Bearer {TURSO_TOKEN}",
                "Content-Type": "application/json",
            },
            json={
                "requests": [
                    {"type": "execute", "stmt": stmt},
                    {"type": "close"},
                ]
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        exec_res = data["results"][0]
        if exec_res.get("type") == "error":
            raise RuntimeError(exec_res.get("error", {}).get("message", "Turso query error"))

        result = exec_res.get("response", {}).get("result", {})
        cols = [c["name"] for c in result.get("cols", [])]
        rows = result.get("rows", [])
        return [
            {col: _decode_val(row[idx]) for idx, col in enumerate(cols)}
            for row in rows
        ]

    db_file = Path(SQLITE_PATH)
    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.execute(sql, args)
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def _row_to_product(row: dict) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "description": row["description"],
        "card_note": row["card_note"],
        "category": row["category"],
        "image": row["image"],
        "min_qty": int(row["min_qty"] or 1),
        "variants": json.loads(row["variants_json"] or "[]"),
        "attributes": json.loads(row["attributes_json"] or "[]"),
    }


def get_products(include_inactive: bool = False) -> list[dict]:
    """Fetch products from DB table if available; otherwise return PRODUCTS from products.py."""
    try:
        if include_inactive:
            rows = _query_db("SELECT * FROM products ORDER BY sort_order ASC, name ASC")
        else:
            rows = _query_db(
                "SELECT * FROM products WHERE is_active = 1 ORDER BY sort_order ASC, name ASC"
            )
        if rows:
            return [_row_to_product(r) for r in rows]
    except Exception:
        pass

    return PRODUCTS