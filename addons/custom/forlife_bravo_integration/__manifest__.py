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
        'queue_job'
    ],
    'auto_install': True,

    'data': [
        'security/ir.model.access.csv',
    ],
    'external_dependencies': {
        'python': ['pyodbc'],
    },
}
