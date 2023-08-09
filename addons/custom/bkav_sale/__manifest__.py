# -*- coding: utf-8 -*-
{
    "name": "BKAV Sale",
    "category": "BKAV",
    "version": "1.3.1",
    'license': 'LGPL-3',
    "sequence": 1,
    "description": """BKAV Sale""",
    "depends": [
        'bkav_connector', 
        'account_debit_note',
    ],
    "data": [
        'views/account_move_views.xml',
    ],
}
