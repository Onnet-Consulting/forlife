# -*- coding: utf-8 -*-
{
    "name": "BKAV Stock Summary",
    "category": "BKAV Stock Summary",
    "version": "16",
    'license': 'LGPL-3',
    "description": """BKAV Stock Summary""",
    "depends": ['bkav_stock'],
    "data": [
        'security/ir.model.access.csv',
        'data/ir_cron_transfer.xml',
        'views/transfer_not_exists_bkav.xml',
    ]
}
