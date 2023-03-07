# -*- coding: utf-8 -*-
{
    'name': "Bravo Integration",

    'summary': """""",

    'description': """
    """,

    'author': "ForLife",
    'website': "",
    "license": "LGPL-3",

    'category': 'Tools',
    'version': '16.0.1.0.0',

    'depends': [
        'queue_job',
        'stock',
        'sale_management',
        'forlife_base',
    ],
    'auto_install': True,

    'data': [
        'security/ir.model.access.csv',
        'views/res_config_settings.xml',
    ],
    'external_dependencies': {
        'python': ['pyodbc'],
    },
}
