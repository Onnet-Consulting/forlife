# -*- coding: utf-8 -*-
{
    "name": "BKAV Connector",
    "category": "BKAV",
    "version": "1.3.1",
    "sequence": 1,
    "description": """BKAV Connector""",
    "depends": ['base', 'forlife_purchase'],
    "data": [
        'data/schedule.xml',
        'views/invoice_view.xml',
    ],
    "application": True,
    "installable": True,
    "auto_install": False,
}
