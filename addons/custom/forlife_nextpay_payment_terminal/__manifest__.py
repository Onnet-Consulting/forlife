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

    'depends': [
        'forlife_payment_terminal_base',
    ],
    'data': [
        'views/res_config_settings_views.xml',
    ],
    'assets': {
        'point_of_sale.assets': [
            'forlife_nextpay_payment_terminal/static/**/*',
        ],
    },
    'external_dependencies': {
        'python': ['pycryptodome'],
    },
}
