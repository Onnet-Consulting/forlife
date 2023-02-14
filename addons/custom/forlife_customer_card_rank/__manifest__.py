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
        'point_of_sale',
        'forlife_point_of_sale',
        'forlife_promotion',
        'forlife_pos_app_member',
    ],

    'data': [
        'security/customer_card_rank_security.xml',
        'security/ir.model.access.csv',
        'data/card_rank_data.xml',
        'data/cron_job_data.xml',

        'views/card_rank_views.xml',
        'views/member_card_views.xml',
        'views/partner_card_rank_views.xml',
        'views/res_partner_views.xml',
        'views/menuitem.xml',
    ]
}
