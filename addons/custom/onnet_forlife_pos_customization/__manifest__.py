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

    'category': 'Point of Sale customization',

    'depends': [
        'point_of_sale'
    ],

    'data': [
    ],
    'installable': True,
    'application': True,
    'assets': {
        'point_of_sale.assets': [
            'onnet_forlife_pos_customization/static/src/js/popup.js',
            'onnet_forlife_pos_customization/static/src/xml/Popups/CashMovePopup.xml',
        ]
    }
}
