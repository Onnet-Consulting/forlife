# -*- coding: utf-8 -*-
{
  "name":  "Forlife Stock",
  "category":  "Forlife Stock",
  "version":  "1.3.1",
  "sequence":  6,
  "description":  """Forlife Stock""",
  "depends":  [
      'hr',
      'purchase_request',
      'product',
      'base',
      'stock',
  ],
  "data":  [
      'data/data_stock_location_type.xml',
      'data/data_stock_location.xml',
      'data/forlife_reason_type_data.xml',
      'security/ir.model.access.csv',
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
      'views/menu.xml'
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
