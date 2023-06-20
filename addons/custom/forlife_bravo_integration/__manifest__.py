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
        'currency_rate_live',
        'queue_job',
        'queue_job_cron',
        'web_map',
        'forlife_base',
        'forlife_pos_app_member',
        'forlife_purchase',
        'forlife_stock',
        'forlife_voucher',
        'forlife_product',
        'forlife_invoice',
        'forlife_pos_popup_cash',
    ],
    'auto_install': True,

    'data': [
        'security/ir.model.access.csv',
        'data/res_partner_group_data.xml',
        'data/queue_job_data.xml',
        'data/ir_cron_data.xml',
        'data/res_brand_data.xml',
        'views/res_config_settings.xml',
        'wizard/bravo_sync_account_wizard_views.xml',
        'wizard/bravo_sync_tax_wizard_views.xml',
        'views/product_category_views.xml',
        'wizard/bravo_sync_asset_wizard_views.xml',
    ],
    'external_dependencies': {
        'python': ['pyodbc'],
    },
}
