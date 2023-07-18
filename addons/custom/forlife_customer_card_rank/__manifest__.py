# -*- coding: utf-8 -*-
{
    'name': "Forlife Rank Customer Card",

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
        'forlife_base',
        'point_of_sale',
        'forlife_point_of_sale',
        'forlife_promotion',
        'forlife_pos_app_member',
        'forlife_pos_promotion',
        'forlife_pos_point_order',
        'queue_job',
    ],

    'data': [
        'security/customer_card_rank_security.xml',
        'security/ir.model.access.csv',
        'data/card_rank_data.xml',
        'data/cron_job_data.xml',
        'data/ir_attachment_data.xml',

        'views/card_rank_views.xml',
        'views/member_card_views.xml',
        'views/partner_card_rank_views.xml',
        'views/res_partner_views.xml',
        'views/pos_order_views.xml',
        'views/promotion_program_views.xml',
        'views/accumulate_by_rank_views.xml',
        'views/points_promotion_views.xml',
        'views/menuitem.xml',

        'wizard/import_partner_card_rank_views.xml',
    ],
    'assets': {
        'point_of_sale.assets': [
            'forlife_customer_card_rank/static/src/css/expand_pos.css',
            'forlife_customer_card_rank/static/src/js/**/*.js',
            'forlife_customer_card_rank/static/src/xml/**/*.xml',
        ],
    },
}
