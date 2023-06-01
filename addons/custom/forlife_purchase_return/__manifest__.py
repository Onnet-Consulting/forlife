# -*- coding: utf-8 -*-
{
    "name": "Forlife Purchase Return",
    "category": "Purchases",
    "version": "1.0.0",
    "description": """Forlife Purchase Return""",
    "depends": [
        'forlife_purchase',
        'purchase_request',
        'stock'
    ],
    "data": [
        'security/ir.model.access.csv',
        'data/purchase_data.xml',
        'wizard/stock_return_picking.xml',
        'wizard/purchase_return_wizard.xml',
        'views/purchase_order_views.xml',
    ],
    "assets": {
    },
    "application": True,
    "installable": True,
    "auto_install": False,
}
