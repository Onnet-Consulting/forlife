# -*- coding: utf-8 -*-
{
    'name': "Promotion",

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
        'point_of_sale', # fixme depend forlife_point_of_sale
    ],

    'data': [
        'security/promotion_security.xml',
        'security/ir.model.access.csv',
        'data/cron_job_data.xml',
        'data/master_data.xml',

        'views/points_promotion_views.xml',
        'views/event_views.xml',
        'views/points_product_views.xml',
        'views/points_product_line_views.xml',

        'views/menuitem.xml',
    ]
}
