# -*- coding: utf-8 -*-
{
    'name': "Redis Integration",

    'summary': """""",

    'description': """
    """,

    'author': "ForLife",
    'website': "",
    "license": "LGPL-3",

    'category': 'Tools',
    'version': '16.0.1.0.0',

    'depends': ['base', 'queue_job', 'stock', 'forlife_stock'],
    'auto_install': True,

    'data': [
        'security/ir.model.access.csv',
        'data/redis_action_key_data.xml',
        'data/queue_job_data.xml',
        'views/redis_host_views.xml',
        'views/redis_action_key_views.xml',
    ],
    'external_dependencies': {
        'python': ['redis'],
    },
}
