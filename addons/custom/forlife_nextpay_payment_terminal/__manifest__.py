# -*- coding: utf-8 -*-
{
    'name': "NextPay payment terminal",

    'summary': """""",

    'description': """
    """,

    'author': "ForLife",
    'website': "",
    "license": "LGPL-3",

    'category': 'Generic Modules',
    'version': '16.0.1.0.0',

    'depends': ['point_of_sale', 'base_automation'],
    'data': [
        'views/res_config_settings_views.xml',
    ],
    'assets': {
        'point_of_sale.assets': [
            'forlife_nextpay_payment_terminal/static/**/*',
        ],
    },
}
