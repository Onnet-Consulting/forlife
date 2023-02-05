# -*- coding: utf-8 -*-
{
    'name': "Point of Sale Forlife Point Order",

    'summary': """Point of Sale Forlife Point Order
        """,

    'description': """
    """,

    'author': "ForLife",
    'website': "",
    "license": "LGPL-3",
    'version': '16.0.1.0,0',

    'category': 'Point of Sale Point Order',

    'depends': [
        'point_of_sale',
        'forlife_point_of_sale',
        'forlife_pos_app_member',
        'forlife_promotion',
        'base'
    ],

    'data': [
        'views/res_partner_view.xml',
        'security/ir.model.access.csv',
        'views/account_move.xml',
        'wizards/pos_compensate_point_views.xml',
        'views/pos_order.xml',
    ],
    'installable': True,
    'application': True,
    # 'assets': {
    # }
}
