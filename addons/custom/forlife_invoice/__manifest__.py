# -*- coding: utf-8 -*-
{
    "name": "Forlife Invoice",
    "category": "Invoice",
    "version": "1.3.1",
    'license': 'LGPL-3',
    "sequence": 1,
    "description": """Forlife Invoice""",
    "depends": [
        'account',
        'purchase',
        'base',
        # 'forlife_purchase',
        'forlife_stock',
    ],
    "data": [
        'data/ir_attachment_data.xml',
        'security/ir.model.access.csv',
        'wizard/import_vendor_back_view.xml',

        'views/invoice_view.xml',
        'views/account_tax_view.xml',
        'views/menus.xml',
        'security/expense_security.xml',
        'views/expense_category_views.xml',
        'views/expense_item_views.xml',
        'views/stock_location.xml',
        'views/account_move_reversal_import_views.xml',
        'wizard/wizard_increase_decrease_invoice_view.xml',
    ],
    "assets": {
        "web.assets_backend": [
            'forlife_invoice/static/src/css/common_invoice.scss',
        ]
    },
    "application": True,
    "installable": True,
    "auto_install": False,
}
