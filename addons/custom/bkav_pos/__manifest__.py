# -*- coding: utf-8 -*-
{
    "name": "BKAV POS General",
    "category": "BKAV",
    "version": "1.3.1",
    'license': 'LGPL-3',
    "sequence": 1,
    "description": """BKAV POS General""",
    "depends": ['base', 'account','point_of_sale','bkav_connector','forlife_invoice','forlife_point_of_sale'],
    "data": [
        'security/ir.model.access.csv',
        'data/schedule.xml',
        'views/store.xml',
        'views/summary_account_move_pos.xml',
        'views/summary_account_move_pos_return.xml',
        'views/synthetic_account_move_pos.xml',
        'views/summary_adjusted_invoice_pos_view.xml',
    ],
}
