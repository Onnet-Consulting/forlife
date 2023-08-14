# -*- coding: utf-8 -*-
{
    "name": "BKAV Stock",
    "category": "BKAV Stock",
    "version": "16",
    'license': 'LGPL-3',
    "description": """BKAV Stock""",
    "depends": [
        'forlife_stock',
        'bkav_connector',
    ],
    "data": [
        'security/ir.model.access.csv',
        'data/ir_cron_contract.xml',
        'views/vendor_contract.xml',
        'views/stock_transfer.xml',
    ]
}
