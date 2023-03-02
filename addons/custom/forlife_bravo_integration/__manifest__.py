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
        'base',
        'queue_job',
        'stock',
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
