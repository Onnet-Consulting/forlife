# -*- coding: utf-8 -*-
{
    "name": "BKAV POS",
    "category": "BKAV",
    "version": "1.3.1",
    'license': 'LGPL-3',
    "sequence": 1,
    "description": """BKAV POS""",
    "depends": ['base', 'account','point_of_sale','bkav_connector','forlife_invoice','forlife_pos_product_change_refund'],
    "data": [
        'views/store.xml',
        'views/pos_order_views.xml',
    ],
}
