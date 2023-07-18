{
    'name': 'Purchase Request',
    'summary': 'Purchase Request',
    'category': 'Inventory/Purchase',
    'depends': [
        'base_automation',
        'forlife_purchase',
        'auth_signup',
        'hr',
        'mrp',
        'stock'
    ],
    'data': [
        'security/purchase_security.xml',
        'security/ir.model.access.csv',
        'security/purchase_security.xml',
        'security/production_order_security.xml',
        'wizards/reject_purchase_request.xml',
        'wizards/cancel_purchase_request.xml',
        'wizards/select_type_po.xml',
        'data/mail_template.xml',
        'data/base_automation.xml',
        'report/purchase_request_report_template.xml',
        'report/purchase_request_reports.xml',
        'views/purchase_request.xml',
        'views/purchase_order.xml',
        'views/product_supplier.xml',
        'views/production_order_view.xml',
        'views/product_product_view.xml',
        'views/purchase_material.xml',
        'views/menus.xml',
        'views/purchase_views.xml'
    ],
    'assets': {
        'web.assets_backend': [
            'purchase_request/static/src/css/approval_logs.css',
        ],
    },
    'installable': True,
    'application': True,
}
