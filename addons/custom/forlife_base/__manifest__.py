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
        'hr',
        'contacts',
        'purchase'
    ],
    'installable': True,
    'auto_install': True,
    'data': [
        'security/ir.model.access.csv',
        'data/mail_activity_type_data.xml',
        'data/res_partner_data.xml',
        'data/product_category_data.xml',
        'data/stock_warehouse_data.xml',

        'views/hr_department_views.xml',
        'views/res_company_views.xml',
        'views/res_partner_views.xml',
        'views/product_category_views.xml',
        'views/product_product_views.xml',
        'views/stock_warehouse_views.xml',
        'views/menu_item.xml',
    ],
    "post_init_hook": "post_init_hook",
}
