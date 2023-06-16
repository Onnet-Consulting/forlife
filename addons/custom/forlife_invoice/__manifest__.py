# -*- coding: utf-8 -*-
{
    "name": "Forlife Invoice",
    "category": "Invoice",
    "version": "1.3.1",
    "sequence": 1,
    "description": """Forlife Invoice""",
    "depends": [
        'account',
        'purchase',
        'base',
        # 'forlife_purchase',
        'forlife_stock',
        'bkav_connector',
    ],
    "data": [
        'views/invoice_view.xml',
        'views/account_tax_view.xml',
        'views/menus.xml',
        'security/ir.model.access.csv',
    ],
    "assets": {
        "web.assets_backend": [

        ]
    },
    "application": True,
    "installable": True,
    "auto_install": False,
}
