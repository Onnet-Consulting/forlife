# -*- coding: utf-8 -*-
{
    'name': "Stock inventory",
    'summary': """Kiểm kê kho""",

    'description': """Kiểm kê kho""",
    'category': 'Sales/Sales',
    'version': '15.0.1.0.0',
    'license': 'LGPL-3',
    # any module necessary for this one to work correctly
    'depends': ['base','purchase', 'sale', 'stock', 'forlife_base', 'report_xlsx'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'security/stock_security.xml',

        'data/ir_attachment_data.xml',

        'wizard/filter_product_wizard_views.xml',
        'wizard/import_inventory_session_views.xml',
        'wizard/request_confirmation_picking_wizard_views.xml',

        'views/stock_inventory_stock_views.xml',
        'views/inventory_detail_views.xml',
        'views/inventory_session_views.xml',

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
