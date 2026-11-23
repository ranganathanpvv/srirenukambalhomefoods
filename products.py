# Pack sizes and prices ending in 3, 4, or 7 (35% margin basis, including base packaging and base delivery allowance).
# Selecting 2 x 250g automatically applies the 500g pack price.

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
        "description": "Homemade lemon pickle, prepared on request. Base delivery included.",
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
    }
]