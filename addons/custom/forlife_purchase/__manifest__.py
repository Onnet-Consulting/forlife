# -*- coding: utf-8 -*-
{
  "name":  "Forlife Purchase",
  "category":  "Purchases",
  "version":  "1.3.1",
  "sequence":  1,
  "description":  """Forlife Purchase""",
  "depends":  [
      'purchase',
      'product',
      'base'
  ],
  "data":  [
      'data/barcode_country_data.xml',
      'security/ir.model.access.csv',
      'views/purchase_order_view.xml',
      'views/cost_center_view.xml',
      'views/forlife_event_view.xml',
      'views/forlife_production_view.xml',
      'views/forlife_bom.xml',
      'views/product_view.xml',
      'views/invoice_view.xml',
      'views/payment_view.xml',
      'views/stock_picking_view.xml',
      'views/res_partner_view.xml',
      'views/stock_warehouse_view.xml',
      'wizard/account_payment_register_view.xml',
      'report/purchase_order_templates.xml',
    ],
    "assets": {
        "web.assets_backend": [

        ]
    },
    "application": True,
    "installable": True,
    "auto_install": False,
}
