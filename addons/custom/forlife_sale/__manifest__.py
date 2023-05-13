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
        'stock',
        'forlife_base'
    ],
    'installable': True,
    'application': True,
    'data': [
        'views/sale_order.xml',
        'views/product_template.xml',
        'security/ir.model.access.csv',

    ]
}
