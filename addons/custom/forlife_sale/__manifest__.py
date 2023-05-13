# -*- coding: utf-8 -*-
{
    'name': "Forlife Sale",
    'summary': """
        """,
    'description': """
    """,
    'author': "ForLife",
    'version': '1.0',

    'category': 'SALE ORDER',

    'depends': [
        'base',
        'sale',
        'forlife_base'
    ],
    'installable': True,
    'application': True,
    'data': [
        'views/sale_order.xml',
        'security/ir.model.access.csv',

    ]
}
