# -*- coding: utf-8 -*-
{
    'name': "ForLife Reports",

    'summary': """""",

    'description': """
    """,

    'author': "ForLife",
    'website': "",
    "license": "LGPL-3",

    'category': 'Generic Modules',
    'version': '16.0.1.0.0',

    'depends': [
        'base', 'stock',
        'report_xlsx',
        'forlife_base',
    ],

    'data': [
        'security/ir.model.access.csv',
        'wizard/report_base_actions.xml',
        'wizard/report_base_views.xml',
        'wizard/report_num1_views.xml',
        'wizard/report_num2_views.xml',
        'wizard/report_num3_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'forlife_report/static/src/xml/**/*',
            'forlife_report/static/src/css/**/*',
            'forlife_report/static/src/js/**/*',
        ]
    }
}
