# -*- coding: utf-8 -*-
{
    'name': "POS Payment Method Change",
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
        "security/ir.model.access.csv",
        "wizards/view_pos_payment_change_wizard.xml",
        # "views/view_pos_config.xml",
        "views/view_pos_order.xml",
        # 'security/forlife_point_of_sale_security.xml',
        # 'security/ir.model.access.csv',
        # 'data/brand_data.xml',
        #
        # 'views/brand_views.xml',
        # 'views/store_views.xml',
        # 'views/pos_config_views.xml',
    ],
    'assets': {
        'point_of_sale.assets': [
            # 'forlife_point_of_sale/static/src/js/*.js',
            # 'forlife_point_of_sale/static/src/xml/*.xml',
            # 'forlife_point_of_sale/static/src/js/popups/*.js',
            # 'forlife_point_of_sale/static/src/xml/popups/*.xml',
        ],
    }
}
