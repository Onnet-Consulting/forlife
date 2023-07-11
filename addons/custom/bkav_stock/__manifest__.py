# -*- coding: utf-8 -*-
{
    "name": "BKAV Stock",
    "category": "BKAV Stock",
    "version": "16",
    "description": """BKAV Stock""",
    "depends": [
        'forlife_stock',
        'bkav_connector',
        'forlife_invoice',
    ],
    "data": [
        'security/ir.model.access.csv',
        'data/ir_cron.xml',
        'views/vendor_contract.xml',
        'views/stock_transfer.xml',
        'views/res_config_settings.xml',
    ]
}
