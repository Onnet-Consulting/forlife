{
    'name': 'Forlife Base',
    'version': '1.0',
    'description': '',
    'summary': '',
    'author': 'ForLife',
    'website': '',
    'license': 'LGPL-3',
    'category': 'Hidden',
    'depends': [
        'base',
        'base_import',
        'hr',
        'contacts',
        'purchase',
        'account',
        'forlife_product',
        'forlife_point_of_sale',
        'base_external_dbsource',
    ],
    'installable': True,
    'auto_install': True,
    'data': [
        'security/ir.model.access.csv',
        'views/asset_location_view.xml',
        'views/occasion.xml',
        'data/mail_activity_type_data.xml',
        'data/res_partner_data.xml',
        'data/product_category_data.xml',
        'data/stock_warehouse_data.xml',
        'data/forlife_app_api_link_data.xml',

        'views/uom_uom_view.xml',
        'views/account_tax_view.xml',
        'views/assets_assets_views.xml',
        'views/res_headbank.xml',
        'views/res_bank_view.xml',
        'views/account_analytic_account.xml',
        'views/product_template_views.xml',
        'views/warehouse_group_views.xml',

        'views/hr_department_views.xml',
        'views/res_company_views.xml',
        'views/res_partner_views.xml',
        'views/product_category_views.xml',
        'views/product_product_views.xml',
        'views/stock_warehouse_views.xml',
        'views/account_move_views.xml',
        'views/res_ward_views.xml',
        'views/forlife_app_api_link_views.xml',
        'views/attribute_code_config_views.xml',
        'views/menu_item.xml',

        'views/ir_ui_menu_view.xml',
        'views/res_groups_view.xml',
    ],
    "post_init_hook": "post_init_hook",
    'assets': {
        'web.assets_backend': [
            'forlife_base/static/src/css/**/*',
            'forlife_base/static/src/js/**/*',
        ]
    },
}
