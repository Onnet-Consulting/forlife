# -*- coding: utf-8 -*-
{
    'name': "Vietinbank Payment POS",

    'summary': """""",

    'description': """
    """,

    'author': "ForLife",
    'website': "",
    "license": "LGPL-3",

    'category': 'Generic Modules',
    'version': '16.0.1.0.0',
    'depends': [
        'point_of_sale',
        'forlife_viettinbank_foreign_exchange_rate',
        'forlife_base'
    ],
    'assets': {
        'point_of_sale.assets': [
            'forlife_pos_vietinbank/static/**/*',
        ],
    },
    'data': [
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'views/vietinbank.xml',
        'views/pos_config.xml',
    ],
}