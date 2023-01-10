# -*- coding: utf-8 -*-
{
    'name': "Point of Sale Forlife",

    'summary': """Point of Sale Forlife
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
        'forlife_promotion',
        'base'
    ],

    'data': [
        'views/pos_order.xml',
    ],
    'installable': True,
    'application': True,
    # 'assets': {
    # }
}
