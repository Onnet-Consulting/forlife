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
        'account_accountant',
        'l10n_vn',
        'purchase_stock',
        'stock',
        'sale_management',
        'queue_job',
        'forlife_base',
        'forlife_pos_app_member',
    ],
    'auto_install': True,

    'data': [
        'security/ir.model.access.csv',
        'views/res_config_settings.xml',
        'wizard/bravo_sync_account_wizard_views.xml',
    ],
    'external_dependencies': {
        'python': ['pyodbc'],
    },
}
