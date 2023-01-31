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
        'forlife_pos_app_member',
        'forlife_promotion',
        'base'
    ],

    'data': [
        'views/pos_order.xml',
        'views/res_partner_view.xml',
        'security/ir.model.access.csv',
        'views/promotion_inherit_view.xml'
    ],
    'installable': True,
    'application': True,
    'assets': {
        'point_of_sale.assets': [
            'forlife_pos_point_order/static/src/xml/OrderDetails.xml',
            'forlife_pos_point_order/static/src/xml/ProductInfo.xml',
        ]
    }
}
