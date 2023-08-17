# -*- coding: utf-8 -*-
{
    "name": "BKAV POS Summary",
    "category": "BKAV",
    "version": "1.3.1",
    'license': 'LGPL-3',
    "sequence": 1,
    "description": """BKAV POS Summary""",
    "depends": ['bkav_pos', 'bkav_sale'],
    "data": [
        'security/ir.model.access.csv',
        'data/schedule.xml',
        'data/ir_sequence_data.xml',
        'views/summary_account_move_pos.xml',
        'views/summary_account_move_pos_return.xml',
        'views/synthetic_account_move_pos.xml',
        'views/summary_adjusted_invoice_pos_view.xml',
    ],
}
