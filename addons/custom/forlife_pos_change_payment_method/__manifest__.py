# -*- coding: utf-8 -*-
{
    'name': "POS change payment method",

    'summary': "POS change payment method",

    'description': """
    """,

    'author': "Onnet",
    'website': "on.net.vn",
    "license": "LGPL-3",
    'version': '1.0.0',

    'depends': [
        'point_of_sale'
    ],

    'data': [
    ],
    'installable': True,
    'application': True,
    'assets': {
        'point_of_sale.assets': [
            'forlife_pos_change_payment_method/static/src/js/*.js',
            'forlife_pos_change_payment_method/static/src/xml/*.xml',
        ]
    }
}
