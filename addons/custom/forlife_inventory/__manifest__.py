# -*- coding: utf-8 -*-
{
    "name": "Forlife Inventory",
    "category": "Forlife Inventory",
    "version": "1.0.0",
    "description": """Forlife Inventory""",
    "depends": [
        'forlife_stock',
        'stock_inventory'
    ],
    "data": [
        'security/ir.model.access.csv',
        'data/stock_location.xml',
        'views/stock_location_view.xml',
        'views/location_mapping_view.xml'
    ],
    "application": True,
    "installable": True,
    "auto_install": False,
}
