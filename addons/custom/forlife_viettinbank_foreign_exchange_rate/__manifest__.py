# -*- coding: utf-8 -*-
{
    'name': "VietinBank Foreign Exchange Rate",

    'summary': """""",

    'description': """
    """,

    'author': "ForLife",
    'website': "",
    "license": "LGPL-3",

    'category': 'Generic Modules',
    'version': '16.0.1.0.0',

    'depends': ['currency_rate_live'],
    'data': [
        'data/res_company.xml',
        'views/res_config_settings_views.xml',
    ],
    "auto_install": True,
    'external_dependencies': {
        'python': ['pycryptodome'],
    },
}
