# -*- coding: utf-8 -*-
{
    "name": "BKAV Connector",
    "category": "BKAV",
    "version": "1.3.1",
    "sequence": 1,
    "description": """BKAV Connector""",
    "depends": ['base', 'account', 'product', 'forlife_purchase', 'point_of_sale', 'nhanh_connector'],
    "data": [
        'security/ir.model.access.csv',
        'data/schedule.xml',
        'views/invoice_view.xml',
        'views/invoice_not_exists_bkav_view.xml',
        'views/res_config_settings_views.xml',
        'views/store.xml',
        'views/summary_account_move_pos.xml',
        'views/summary_account_move_pos_return.xml',
        'views/synthetic_account_move_pos.xml',
    ],
    "application": True,
    "installable": True,
    "auto_install": False,
}
