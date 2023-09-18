# -*- coding: utf-8 -*-
{
    "name": "Forlife Purchase",
    "category": "Purchases",
    "version": "1.3.1",
    'license': 'LGPL-3',
    "sequence": 1,
    "description": """Forlife Purchase""",
    "depends": [
        'hr',
        'purchase',
        'product',
        'base',
        'forlife_base',
        'purchase_stock',
        'forlife_pos_app_member',
        'web_domain_field',
        'l10n_vn',
        'sale',
        'report_xlsx',
    ],
    "data": [
        'data/product_category.xml',
        'data/barcode_country_data.xml',
        'security/purchase_security.xml',
        'security/ir.model.access.csv',
        'wizard/reject_purchase_order.xml',
        'wizard/cancel_purchase_order.xml',
        'wizard/select_type_invoice.xml',
        'wizard/import_tax_info_wizard_views.xml',
        'views/purchase_order_view.xml',
        'views/forlife_event_view.xml',
        'views/forlife_production_view.xml',
        'views/production_history_view.xml',
        'views/forlife_bom.xml',
        'views/stock_warehouse_type.xml',
        'views/product_view.xml',
        'views/res_partner_view.xml',
        'views/stock_warehouse_view.xml',
        'views/synthetic_view.xml',
        'report/purchase_order_templates.xml',
        'views/product_supplierinfo_views.xml',
        'views/stock_picking_view.xml',
        'views/production_import.xml',
        'wizard/import_production.xml',
        'report/print_production.xml',
    ],
    "assets": {
        "web.assets_backend": [
            '/forlife_purchase/static/src/css/common.scss',
            'forlife_purchase/static/src/xml/import_button.xml',
        ],
        'web.assets_qweb': [
        ],
    },
    "application": True,
    "installable": True,
    "auto_install": False,
}
