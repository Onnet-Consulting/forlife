# -*- coding: utf-8 -*-
{
    "name": "Forlife Stock Report",
    "category": "Forlife Stock",
    "version": "1.3.1",
    'license': 'LGPL-3',
    "sequence": 6,
    "description": """Forlife Stock Report""",
    "depends": [
        'forlife_stock',
        'base',
        'stock',
        'stock_account'
    ],
    "data": [
        'security/ir.model.access.csv',
        'reports/outgoing_value_diff_report.xml',
        'reports/stock_incoming_outgoing_report.xml',
        'reports/stock_balance_difference_report_views.xml',
        'views/stock_quant_period.xml',
        'views/product_product.xml',
        'views/product_template.xml',
    ]
}
