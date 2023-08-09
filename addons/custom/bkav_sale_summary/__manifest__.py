# -*- coding: utf-8 -*-
{
    "name": "BKAV Sale Summary",
    "category": "BKAV",
    "version": "1.3.1",
    'license': 'LGPL-3',
    "sequence": 1,
    "description": """BKAV Sale Summary""",
    "depends": [
        'bkav_sale',
        'nhanh_connector',
    ],
    "data": [
        'security/ir.model.access.csv',
        'data/schedule.xml',
        'data/ir_sequence_data.xml',
        # 'views/invoice_not_exists_bkav_view.xml',
        'views/summary_account_move_so_nhanh.xml',
        'views/summary_account_move_so_nhanh_return.xml',
        'views/synthetic_account_move_so_nhanh.xml',
        'views/summary_adjusted_invoice_so_nhanh.xml',
        'views/account_invoicing_menus.xml',
    ],
}
