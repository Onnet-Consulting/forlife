{
    'name': 'Forlife Permission Management',
    'version': '1.0',
    'description': '',
    'summary': '',
    'author': 'ForLife',
    'website': '',
    'license': 'LGPL-3',
    'category': 'Hidden',
    'depends': [
        'base',
        'product',
        'purchase_request',
        'forlife_stock',
        'forlife_pos_product_change_refund',
        'point_of_sale',
        'forlife_pos_product_change_refund',
    ],
    'installable': True,
    'auto_install': True,
    'data': [
        'security/forlife_permission_management_security.xml',
        'security/ir.model.access.csv',
        'security/forlife_permission_rule.xml',
        'data/menu.xml',
        'views/product_product_views.xml',
        'views/res_users_views.xml',
        'views/hr_team_views.xml',
        'views/pos_order_views.xml',
        'views/pos_session_views.xml',
        'views/pos_payment_views.xml',
    ],
}
