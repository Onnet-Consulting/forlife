# -*- coding: utf-8 -*-
{
    "name": "Forlife Inventory",
    "category": "Forlife Inventory",
    "version": "1.0.0",
    'license': 'LGPL-3',
    "description": """Forlife Inventory""",
    "depends": [
        'forlife_stock',
        'stock_inventory'
    ],
    "data": [
        'security/ir.model.access.csv',
        'views/stock_inventory_view.xml',
        'views/stock_location_view.xml',
        'views/location_mapping_view.xml'
    ],
    "application": True,
    "installable": True,
    "auto_install": False,
}
