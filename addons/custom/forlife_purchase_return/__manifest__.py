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
        'wizard/stock_return_picking.xml',
        'views/purchase_order_views.xml',
    ],
    "assets": {
    },
    "application": True,
    "installable": True,
    "auto_install": False,
}
