# -*- coding: utf-8 -*-
{
    'name': "Stock inventory",
    'summary': """Kiểm kê kho""",

    'description': """Kiểm kê kho""",
    'category': 'Sales/Sales',
    'version': '15.0.1.0.0',
    # any module necessary for this one to work correctly
    'depends': ['base','purchase', 'sale', 'stock'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'security/stock_security.xml',
        'views/stock_inventory_stock_views.xml',
        'reports/report_stockinventory.xml',
        'reports/report_stock_valorization.xml',
    ],
    'assets': {

        'web.assets_backend': [
                'stock_inventory/static/src/js/inventory_validate_button_controller.js',
                'stock_inventory/static/src/js/inventory_validate_button_view.js',
            ],
        'web.assets_qweb': [
                'stock_inventory/static/src/xml/inventory_lines.xml',
            ],
    },
}
