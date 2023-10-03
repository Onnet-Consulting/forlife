# -*- coding: utf-8 -*-
{
    "name": "Forlife POS Import Order",
    "category": "Forlife POS Import Order",
    "version": "1.0.0",
    'license': 'LGPL-3',
    "depends": [
        'forlife_base',
    ],
    "data": [
        'wizard/pos_order_import.xml',
    ],
    "assets": {
        "web.assets_backend": [
            'forlife_import_pos_order/static/src/xml/import_button.xml',
        ],
        'web.assets_qweb': [
        ],
    },
    "application": True,
    "installable": True,
    "auto_install": False,
}
