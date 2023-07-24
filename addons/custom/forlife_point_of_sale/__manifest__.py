# -*- coding: utf-8 -*-
{
    'name': "ForLife Point of Sales",

    'summary': """
        """,

    'description': """
    """,

    'author': "ForLife",
    'website': "",
    "license": "LGPL-3",
    'version': '16.0.1.0,0',

    'category': 'Sales/Point of Sale',

    'depends': [
        'point_of_sale',
        'hr',
        'queue_job',
    ],

    'data': [
        'security/forlife_point_of_sale_security.xml',
        'security/ir.model.access.csv',
        'data/brand_data.xml',
        'data/ir_attachment_data.xml',

        'views/brand_views.xml',
        'views/store_views.xml',
        'views/pos_config_views.xml',
        'views/res_partner_views.xml',
        'views/pos_order_views.xml',
        'views/product_attribute_view.xml',
        'data/mail_template.xml',
        'data/cron.xml',
        'views/ir_cron_views.xml',
        'views/account_move_views.xml',

        'wizard/import_store_first_order_views.xml',
    ],
    'assets': {
        'point_of_sale.assets': [
            'forlife_point_of_sale/static/src/js/*.js',
            'forlife_point_of_sale/static/src/xml/*.xml',
            'forlife_point_of_sale/static/src/css/*.css',
        ],
    }
}
