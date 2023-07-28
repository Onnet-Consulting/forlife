# -*- coding: utf-8 -*-
{
    "name": "Nhanh Connector",
    "category": "Purchases",
    "version": "1.3.1",
    'license': 'LGPL-3',
    "sequence": 1,
    "description": """Nhanh Connector""",
    "depends": [
        'sale', 
        'base', 
        'sale_management', 
        'forlife_pos_app_member', 
        'product', 
        'forlife_stock', 
        'utm',
        'forlife_pos_promotion',
        'forlife_point_of_sale',
    ],
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
        'wizards/disable_nhanh_product.xml',
        'wizards/import_transport.xml',
        'views/product_category_type.xml',
        'views/utm_source.xml',
        'views/promotion_campaign.xml',
        'views/delivery_carrier.xml',
        'views/stock_picking.xml',
        'views/sale_channel_view.xml',
        'views/sale_menus.xml',
        'data/sale_channel_data.xml',
        'data/queue_job_data.xml',
        'views/transportation_management.xml',
    ],
    "assets": {
        "web.assets_backend": [
            'nhanh_connector/static/src/xml/import_button.xml',
        ],
        'web.assets_qweb': [
        ],
    },
    "application": True,
    "installable": True,
    "auto_install": False,
}
