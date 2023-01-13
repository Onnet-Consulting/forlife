{
    'name': 'Purchase Request',
    'summary': 'Purchase Request',
    'category': 'Inventory/Purchase',
    'depends': [
        'forlife_purchase',
        'auth_signup',
        'hr'
    ],
    'data': [
        'security/ir.model.access.csv',
        'wizards/reject_purchase_request.xml',
        'data/mail_template.xml',
        'report/purchase_request_report_template.xml',
        'report/purchase_request_reports.xml',
        'views/purchase_request.xml',
        'views/purchase_order.xml',
        'views/product_supplier.xml',
        'views/menus.xml',

    ],
    'assets': {
        'web.assets_backend': [
            'purchase_request/static/src/css/approval_logs.css',
        ],
    },
    'installable': True,
    'application': True,
}
