# -*- coding: utf-8 -*-
{
    "name": "Forlife Purchase",
    "category": "Purchases",
    "version": "1.3.1",
    "sequence": 1,
    "description": """Forlife Purchase""",
    "depends": [
        'hr',
        'purchase',
        'product',
        'base',
        'forlife_base',
        'purchase_stock',
        'web_domain_field'
    ],
    "data": [
        'data/barcode_country_data.xml',
        'security/purchase_security.xml',
        'security/ir.model.access.csv',
        'wizard/reject_purchase_order.xml',
        'views/purchase_order_view.xml',
        'views/forlife_event_view.xml',
        'views/forlife_production_view.xml',
        'views/forlife_bom.xml',
        'views/stock_warehouse_type.xml',
        'views/product_view.xml',
        'views/res_partner_view.xml',
        'views/stock_warehouse_view.xml',
        # 'wizard/account_payment_register_view.xml',
        'report/purchase_order_templates.xml',
        'views/product_supplierinfo_views.xml',
        'views/hr_employee_views.xml',
    ],
    "assets": {
        "web.assets_backend": [
            '/forlife_purchase/static/src/css/common.scss',
        ],
        'web.assets_qweb': [
        ],
    },
    "application": True,
    "installable": True,
    "auto_install": False,
}
