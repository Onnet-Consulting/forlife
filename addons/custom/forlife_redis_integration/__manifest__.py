# -*- coding: utf-8 -*-
{
    'name': "Redis Integration",

    'summary': """""",

    'description': """
    """,

    'author': "ForLife",
    'website': "",
    "license": "LGPL-3",

    'category': 'Generic Modules',
    'version': '16.0.1.0.0',

    'depends': ['base'],
    'auto_install': True,

    'data': [
        'security/ir.model.access.csv',
        'views/integration_redis_views.xml',
    ],
    'external_dependencies': {
        'python': ['redis'],
    },
}
