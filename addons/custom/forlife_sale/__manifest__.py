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
        'account',
        'forlife_base'
    ],
    'installable': True,
    'application': True,
    'data': [
        'wizard/create_sale_order_punish.xml',
        'views/account_move.xml',
        'views/product_pricelist.xml',
        'views/sale_order.xml',
        'views/product_template.xml',
        'security/ir.model.access.csv',

    ]
}
