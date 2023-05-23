# -*- coding: utf-8 -*-
{
    "name": "Forlife Inventory",
    "category": "Forlife Inventory",
    "version": "1.0.0",
    "description": """Forlife Inventory""",
    "depends": [
        'forlife_stock'
    ],
    "data": [
        'security/ir.model.access.csv',
        'views/stock_location_view.xml',
        'views/location_mapping_view.xml'
    ],
    "application": True,
    "installable": True,
    "auto_install": False,
}
