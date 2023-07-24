# -*- coding: utf-8 -*-
{
    "name": "Forlife Stock Exchange",
    "category": "Forlife Stock Exchange",
    'license': 'LGPL-3',
    "description": """Forlife Stock Exchange""",
    "depends": [
        'forlife_stock',
        'forlife_purchase'
    ],
    "data": [
        'data/stock_exchange_data.xml',
        'views/forlife_picking_type_views.xml',
        'views/forlife_stock_exchange_views.xml',
        'views/forlife_menuitems.xml'
    ],
    "assets": {
    },
    "installable": True,
    "auto_install": False,
}
