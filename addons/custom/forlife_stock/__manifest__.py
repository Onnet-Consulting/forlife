# -*- coding: utf-8 -*-
{
    "name": "Forlife Stock",
    "category": "Forlife Stock",
    "version": "1.3.1",
    "sequence": 6,
    "description": """Forlife Stock""",
    "depends": [
        'hr',
        'purchase_request',
        'product',
        'base',
        'stock',
        'stock_account',
        'stock_landed_costs'
    ],
    "data": [
        'data/data_stock_location_type.xml',
        'data/forlife_reason_type_data.xml',
        'data/data_stock_location.xml',
        'security/ir.model.access.csv',
        'reports/outgoing_value_diff_report.xml',
        'reports/stock_incoming_outgoing_report.xml',
        'wizards/reject_stock_transfer_request_view.xml',
        'wizards/reject_transfer_stock_inventory_view.xml',
        'wizards/reject_asset_transfer.xml',
        'data/base_automation.xml',
        'views/stock_transfer_request_view.xml',
        'views/stock_transfer_view.xml',
        'views/stock_location_type_view.xml',
        'views/stock_location_view.xml',
        'views/stock_custom_location_view.xml',
        'views/stock_picking_other_export_view.xml',
        'views/hr_asset_transfer_view.xml',
        'views/transfer_stock_inventory.xml',
        'views/inventory_adj_approval_view.xml',
        'views/product_template.xml',
        'views/menus.xml',
        'views/stock_picking.xml',
        'views/stock_move.xml',
        'views/stock_move_line.xml',
        'views/stock_valuation_layer.xml'
    ],
    "assets": {
        "web.assets_backend": [
            '/forlife_stock/static/src/css/common_stock.scss',
        ],
        'web.assets_qweb': [
        ],
    },
    "application": True,
    "installable": True,
    "auto_install": False,
}
