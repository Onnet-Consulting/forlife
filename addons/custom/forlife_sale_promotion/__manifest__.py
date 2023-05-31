# -*- coding: utf-8 -*-
{
    'name': "Forlife Sale Promotion",
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
        'forlife_base',
        'forlife_sale',
        'nhanh_connector',
        'sale_loyalty'
    ],
    'installable': True,
    'application': True,
    'sequence': 1,
    'data': [
        'data/account.xml',
        'security/ir.model.access.csv',
        'views/sale_order.xml',
        'views/product_view.xml',
        'views/account_move.xml',
        'views/account_journal.xml'
    ]
}
