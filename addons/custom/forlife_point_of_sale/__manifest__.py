# -*- coding: utf-8 -*-
{
    'name': "ForLife Point of Sales",

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
        'hr',
    ],

    'data': [
        'security/forlife_point_of_sale_security.xml',
        'security/ir.model.access.csv',

        'views/store_view.xml',
        'views/pos_config_view.xml',
    ],
    'assets': {
        'point_of_sale.assets': [
            'forlife_point_of_sale/static/src/xml/ProductItem.xml',
            'forlife_point_of_sale/static/src/js/db.js',
        ]
    }
}
