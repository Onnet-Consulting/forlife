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
      'security/ir.model.access.csv',
      'wizards/reject_stock_transfer_request_view.xml',
      'data/base_automation.xml',
      'views/stock_transfer_request_view.xml',
      'views/stock_transfer_view.xml',
      'views/stock_location_type_view.xml',
      'views/stock_location_view.xml',
      'views/hr_asset_transfer_view.xml',
      'views/menus.xml'
  ],
    "assets": {
        "web.assets_backend": [
        ]
    },
    "application": True,
    "installable": True,
    "auto_install": False,
}
