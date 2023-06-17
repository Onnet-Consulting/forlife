# -*- coding: utf-8 -*-
{
    "name": "Nhanh Connector",
    "category": "Purchases",
    "version": "1.3.1",
    "sequence": 1,
    "description": """Nhanh Connector""",
    "depends": ['sale', 'base', 'sale_management', 'forlife_pos_app_member', 'product', 'forlife_base'],
    "data": [
        'security/ir.model.access.csv',
        'data/cron.xml',
        'views/sale_order_view.xml',
        'views/res_partner_customer_view.xml',
        # 'views/res_config_settings_views.xml',
        'views/nhanh_brand_config.xml',
        'views/nhanh_webhook_value.xml',
        'views/stock_location.xml',
        'views/stock_warehouse.xml',
    ],
    "application": True,
    "installable": True,
    "auto_install": False,
}
