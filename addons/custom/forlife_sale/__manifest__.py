# -*- coding: utf-8 -*-
{
    'name': "Forlife Sale",
    'summary': """
        """,
    'description': """
    """,
    'author': "ForLife",
    'version': '0.1',

    'category': 'SALE ORDER',

    'depends': [
        'base',
        'sale'
    ],
    'installable': True,
    'application': True,
    'data': [
        'views/sale_order.xml',
        'security/ir.model.access.csv',

    ]
}
