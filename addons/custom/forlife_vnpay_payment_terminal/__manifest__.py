# -*- coding: utf-8 -*-
{
    'name': "VNPay payment terminal",

    'summary': """""",

    'description': """
    """,

    'author': "ForLife",
    'website': "",
    "license": "LGPL-3",

    'category': 'Generic Modules',
    'version': '16.0.1.0.0',
    'depends': [
        'forlife_payment_terminal_base',
    ],
    'assets': {
        'point_of_sale.assets': [
            'forlife_vnpay_payment_terminal/static/**/*',
        ],
    },
    'data': [
        'views/res_config_settings_views.xml',
    ],
}
