# -*- coding: utf-8 -*-
{
    "name": "Forlife Splip Products",
    "category": "Forlife Splip Products",
    "version": "1.0.0",
    "description": """Forlife Splip Products""",
    "depends": [
        'account',
        'hr',
        'forlife_stock'
    ],
    "data": [
        'security/ir.model.access.csv',
        'data/ir_sequence.xml',
        'data/data_stock_location.xml',
        'views/split_product_views.xml',
    ],
    "application": True,
    "installable": True,
    "auto_install": False,
}
