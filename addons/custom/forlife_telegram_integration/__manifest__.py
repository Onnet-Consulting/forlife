# -*- coding: utf-8 -*-
{
    'name': "Telegram Integration",

    'summary': """""",

    'description': """
    """,

    'author': "ForLife",
    'website': "",
    "license": "LGPL-3",

    'category': 'Generic Modules',
    'version': '16.0.1.0.0',

    'depends': ['base', 'forlife_base'],
    'auto_install': True,

    'data': [
        'security/ir.model.access.csv',
        'data/telegram_bot_data.xml',
        'data/telegram_group_data.xml',
        'data/integration_telegram_data.xml',

        'views/integration_telegram_views.xml',
        'views/telegram_bot_views.xml',
        'views/telegram_group_views.xml',
    ],
}
