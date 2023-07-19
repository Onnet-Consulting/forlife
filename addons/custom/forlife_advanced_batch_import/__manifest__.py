# -*- coding: utf-8 -*-
{
    'name': "forlife_advanced_batch_import",

    'summary': """
        Advanced batch import""",

    'description': """
        Separate Origin file import to many sub files, and import them
    """,
    'license': 'LGPL-3',

    'author': "thang.dao@on.net.vn",
    'website': "https://on.net.vn/",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/16.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'queue_job', 'base_import', 'product'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/parent_batch_import.xml',
        'views/child_batch_import.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'forlife_advanced_batch_import/static/src/xml/*.xml',
            'forlife_advanced_batch_import/static/src/js/*.js',
        ],
    },
}
