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
        'hr',
        'quality',
        'purchase',
        'analytic',
        'stock_account',
        'stock_enterprise',
        'purchase_request',
        'forlife_base',
        'forlife_stock',
        'forlife_purchase',
        'forlife_stock_report',
        'forlife_pos_product_change_refund',
        'point_of_sale',
    ],
    'installable': True,
    'auto_install': True,
    'data': [
        'security/forlife_permission_management_security.xml',
        'security/ir.model.access.csv',
        'security/forlife_permission_rule.xml',
        'data/action.xml',
        'data/menu.xml',
        'data/groups.xml',
        'views/product_product_views.xml',
        'views/res_users_views.xml',
        'views/hr_team_views.xml',
        'views/pos_order_views.xml',
        'views/pos_session_views.xml',
        'views/pos_payment_views.xml',
        'views/stock_transfer_request_views.xml',
        'views/hr_asset_transfer_views.xml',
        'views/handle_change_refund_views.xml',
        'views/forlife_other_in_out_request_views.xml',
        'views/transfer_stock_inventory_view.xml',
        'views/purchase_material_views.xml',
        'views/purchase_order_views.xml',
        'views/purchase_request_views.xml',
        'views/sale_order_views.xml',
        'views/stock_picking_views.xml',
        'views/product_defective_views.xml',
        'views/stock_inventory_views.xml',
        'views/print_stamps_barcode_view.xml',
    ],
}
