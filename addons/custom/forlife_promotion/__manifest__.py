# -*- coding: utf-8 -*-
{
    'name': "Promotion",

    'summary': """
        """,

    'description': """
    """,

    'author': "ForLife",
    'website': "",
    "license": "LGPL-3",
    'version': '16.0.1.0,0',

    'category': 'Sales/Point of Sale',

    'depends': [
        'point_of_sale',
    ],

    'data': [
        'security/promotion_security.xml',
        'security/ir.model.access.csv',

        'views/points_promotion_views.xml',
        'views/points_promotion_line_views.xml',

        'views/menuitem.xml',
    ]
}
