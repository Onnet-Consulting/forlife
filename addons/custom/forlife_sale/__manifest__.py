# -*- coding: utf-8 -*-
{
    'name': "Forlife Sale",
    'summary': """
        """,
    'description': """
    """,
    'author': "ForLife",
    'version': '1.0',
    'license': 'LGPL-3',

    'category': 'SALE ORDER',

    'depends': [
        'base',
        'sale',
        'stock',
        'product',
        'account',
        'forlife_base'
    ],
    'installable': True,
    'application': True,
    'data': [
        'wizard/create_sale_order_punish.xml',
        'wizard/stock_picking_return.xml',

        'wizard/confirm_return_so.xml',
        # 'views/account_move.xml',
        'views/stock_picking.xml',
        'views/product_pricelist.xml',
        'views/sale_order.xml',
        'views/product_template.xml',
        'views/product_category.xml',
        'views/stock_picking_type.xml',
        'security/ir.model.access.csv',

    ]
}
