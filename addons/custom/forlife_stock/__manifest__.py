# -*- coding: utf-8 -*-
{
    'name': "Stock Forlife",

    'summary': """
        """,

    'description': """
    """,

    'author': "ForLife",
    'website': "",
    "license": "LGPL-3",
    'version': '16.0.1.0,0',

    'category': 'Inventory/Inventory',

    'depends': ['stock_account', 'stock_landed_costs'],

    'data': [
        'security/ir.model.access.csv',
        'views/stock_picking.xml',
        'reports/outgoing_value_diff_report.xml',
        'reports/stock_incoming_outgoing_report.xml',
    ],
    'assets': {
        'web.assets_backend': [
        ]
    },
}
